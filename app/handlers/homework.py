"""Обработчик проверки домашнего задания.

UPDATED 2025-12-28 23:10:
- REPLACED: OCR.space API → LOCAL Tesseract/EasyOCR
- ADDED: Unified OCR Service
- FIXED: JPG recognition now works reliably
- IMPROVED: No SSL errors

UPDATED 2025-12-25 14:45:
- УДАЛЕНы дубли логирования
- Все логирование теперь в replicate_client.py

Handles /homework command for checking student homework.
"""

import logging
from typing import Optional
from pathlib import Path
import base64
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.filters.command import Command
from aiogram.filters.state import StateFilter
from aiogram.enums import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.states.homework import HomeworkStates
from app.services.homework import HomeworkChecker, SubjectCheckers, ResultVisualizer
from app.services.llm.llm_factory import LLMFactory
from app.services.file_processing import PDFParser, DOCXParser
from app.services.ocr import OCRService, OCRQualityLevel
from app.services.prompts.prompt_manager import PromptManager
from app.config import get_settings

logger = logging.getLogger(__name__)

router = Router()
prompt_manager = PromptManager()
config = get_settings()
ocr_service = OCRService()

# Initialize LLMFactory once
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)


def get_subjects_keyboard() -> InlineKeyboardMarkup:
    """Create subjects selection keyboard.
    
    Returns:
        InlineKeyboardMarkup with subjects
    """
    subjects = SubjectCheckers.get_subjects_list()
    buttons = []
    
    for i in range(0, len(subjects), 2):
        row = []
        for j in range(2):
            if i + j < len(subjects):
                subject = subjects[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=f"{subject.emoji} {subject.name}",
                        callback_data=f"hw_subject_{subject.code}"
                    )
                )
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("homework"))
async def start_homework(
    message: Message,
    state: FSMContext
) -> None:
    """Start homework checking flow.
    
    Args:
        message: User message
        state: FSM state
    """
    await state.clear()
    logger.info(f"User {message.from_user.id} started homework mode")
    
    await state.set_state(HomeworkStates.selecting_subject)
    current_state = await state.get_state()
    logger.debug(f"[HOMEWORK DEBUG] User {message.from_user.id}: Set state to {current_state}")
    
    await message.answer(
        text=(
            "📖 <b>Проверка домашнего задания</b>\n\n"
            "Выбери предмет для проверки:\n\n"
            "✍️ <i>Где редактировать промпты:</i>\n"
            "<code>/prompts</code> → Домашка → [Предмет] → Недиктировать"
        ),
        reply_markup=get_subjects_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(
    F.data.startswith("hw_subject_"),
    StateFilter(HomeworkStates.selecting_subject)
)
async def select_subject(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle subject selection.
    
    Args:
        callback: Callback query
        state: FSM state
    """
    subject_code = callback.data.replace("hw_subject_", "")
    
    try:
        subject = SubjectCheckers.get_subject(subject_code)
    except ValueError:
        await callback.answer(
            text="❌ Неизвестный предмет",
            show_alert=True
        )
        return
    
    await state.update_data(subject=subject_code)
    logger.info(f"User {callback.from_user.id} selected subject: {subject_code}")
    
    await callback.message.edit_text(
        text=(
            f"{subject.emoji} <b>{subject.name}</b>\n\n"
            f"💬 {subject.description}\n\n"
            f"<b>📄 Отправьте:</b>\n"
            f"• Текст с решением\n"
            f"• Фото (текст распознается автоматически)\n"
            f"• PDF или DOCX файл\n\n"
            f"✍️ <i>Оредактировать промпт для этого предмета:</i>\n"
            f"<code>/prompts</code> → Домашка → {subject.name} → Недиктировать"
        ),
        parse_mode="HTML",
        reply_markup=None
    )
    
    await state.set_state(HomeworkStates.waiting_for_file)
    new_state = await state.get_state()
    logger.debug(f"[HOMEWORK DEBUG] User {callback.from_user.id}: Set state to {new_state}")
    logger.info(f"User {callback.from_user.id} ready to upload homework for {subject_code}")


@router.message(
    StateFilter(HomeworkStates.waiting_for_file),
    F.content_type.in_({ContentType.DOCUMENT, ContentType.PHOTO, ContentType.TEXT})
)
async def process_homework_file(
    message: Message,
    state: FSMContext
) -> None:
    """Обработка домашки с unified OCR.
    
    Args:
        message: User message with file
        state: FSM state
    """
    data = await state.get_data()
    subject_code = data.get("subject")
    user_id = message.from_user.id
    
    logger.info(f"User {user_id} processing homework for subject: {subject_code}")
    
    processing_msg = await message.answer(
        text=(
            "🔄 Обрабатываю...\n"
            "📄 Нимаю текст...\n"
            "🤖 анализирую ответы...\n\n"
            "✍️ Подсказка: промпты для проверки можно изменить в меню:\n"
            "`/prompts` → Домашка → [Предмет] → Недиктировать`"
        )
    )
    
    try:
        content = await _extract_content(message, user_id)
        
        if not content or not content.strip():
            await processing_msg.edit_text(
                text=(
                    f"❌ Не удалось получить текст\n\n"
                    f"Проверьте:\n"
                    f"• Фото должно быть четким\n"
                    f"• Текст должен быть читаемым\n"
                    f"• Или отправьте текст сообщением"
                )
            )
            await state.clear()
            return
        
        logger.info(f"Homework content: {len(content)} chars for user {user_id}")
        
        # Initialize checker with LLM factory
        checker = HomeworkChecker(llm_factory)
        
        # Load user-specific prompts
        prompt_manager.load_user_prompts(user_id)
        subject_prompt_name = f"{subject_code}_homework"
        homework_prompt = prompt_manager.get_prompt(user_id, subject_prompt_name)
        
        # Determine system prompt
        if homework_prompt:
            system_prompt = homework_prompt.system_prompt
            logger.info(f"Using subject-specific homework prompt: {subject_prompt_name}")
        else:
            logger.warning(f"Homework prompt not found for subject {subject_code}, using default")
            system_prompt = None  # Let HomeworkChecker use its default
        
        # Check homework - HomeworkChecker handles prompt creation internally
        result = await checker.check_homework(
            content=content,
            subject=subject_code,
            file_type="text",
            system_prompt=system_prompt
        )
        
        # Format and send result
        result_text = ResultVisualizer.format_result(result)
        result_text += (
            "\n\n"
            "✍️ Подсказка: текст проверки можно изменить в меню\n"
            "`/prompts` → Домашка → [Предмет] → Недиктировать`"
        )
        
        await processing_msg.edit_text(text=result_text)
        logger.info(f"Homework checked successfully for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing homework: {type(e).__name__}: {str(e)}", exc_info=True)
        await processing_msg.edit_text(text=f"❌ Ошибка: {str(e)}")
    
    await state.clear()


async def _extract_content(message: Message, user_id: int) -> str:
    """Extract content from message using unified OCR."""
    if message.text:
        return message.text
    
    if message.photo:
        return await _extract_text_from_photo(message, user_id)
    
    if message.document:
        return await _extract_text_from_document(message, user_id)
    
    raise ValueError("Неподдерживаемый тип")


async def _extract_text_from_photo(message: Message, user_id: int) -> str:
    """Extract text from photo using unified OCR service."""
    try:
        settings = get_settings()
        
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        
        try:
            # Use unified OCR service (LOCAL Tesseract, no API)
            extracted_text, quality = await ocr_service.extract_from_file(temp_file, user_id)
            
            logger.info(
                f"[OCR QUALITY] User {user_id} (homework): {quality.value} | "
                f"{len(extracted_text)} chars, {len(extracted_text.split())} words"
            )
            
            if quality == OCRQualityLevel.POOR:
                logger.warning(
                    f"[OCR] User {user_id}: Low quality homework OCR"
                )
            
            return extracted_text
        
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    except Exception as e:
        logger.error(f"OCR: Fatal error: {type(e).__name__}: {str(e)}", exc_info=True)
        return ""


async def _extract_text_from_document(message: Message, user_id: int) -> str:
    """Extract text from document file."""
    settings = get_settings()
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(exist_ok=True)
    
    file_info = await message.bot.get_file(message.document.file_id)
    file_path = temp_dir / message.document.file_name
    
    await message.bot.download_file(file_info.file_path, file_path)
    
    try:
        if message.document.mime_type == "application/pdf":
            pdf_parser = PDFParser()
            content = pdf_parser.extract_text(file_path)
        elif message.document.mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            docx_parser = DOCXParser()
            content = docx_parser.extract_text(file_path)
        elif message.document.mime_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            raise ValueError(f"Неподдерживаемый тип: {message.document.mime_type}")
    
    finally:
        if file_path.exists():
            file_path.unlink()
    
    return content
