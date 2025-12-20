"""Homework checking handler.

Handles /homework command for checking student homework.
"""

import logging
from typing import Optional
from pathlib import Path
import base64

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.enums import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.states.homework import HomeworkStates
from app.services.homework import HomeworkChecker, SubjectCheckers, ResultVisualizer
from app.services.llm.replicate_client import ReplicateClient
from app.services.file_processing import PDFParser, DOCXParser
from app.config import get_settings

logger = logging.getLogger(__name__)

router = Router()


def get_subjects_keyboard() -> InlineKeyboardMarkup:
    """Create subjects selection keyboard.
    
    Returns:
        InlineKeyboardMarkup with subjects
    """
    subjects = SubjectCheckers.get_subjects_list()
    buttons = []
    
    # Create 2 columns
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
    await message.answer(
        text=(
            "📖 <b>Проверка домашнего задания</b>\n\n"
            "Выбери предмет для проверки:"
        ),
        reply_markup=get_subjects_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(HomeworkStates.selecting_subject)


@router.callback_query(
    F.data.startswith("hw_subject_"),
    HomeworkStates.selecting_subject
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
    
    # Store subject in state
    await state.update_data(subject=subject_code)
    
    # Update message
    await callback.message.edit_text(
        text=(
            f"{subject.emoji} <b>{subject.name}</b>\n\n"
            f"💬 {subject.description}\n\n"
            f"📄 Отправь файл, фото или текст"
        ),
        parse_mode="HTML",
        reply_markup=None
    )
    
    await state.set_state(HomeworkStates.waiting_for_file)


@router.message(
    HomeworkStates.waiting_for_file,
    F.content_type.in_({ContentType.DOCUMENT, ContentType.PHOTO, ContentType.TEXT})
)
async def process_homework_file(
    message: Message,
    state: FSMContext
) -> None:
    """Process homework file, photo or text.
    
    Args:
        message: User message with file
        state: FSM state
    """
    data = await state.get_data()
    subject_code = data.get("subject")
    
    # Show processing message
    processing_msg = await message.answer(
        text=(
            "🕋 Обрабатываю...\n"
            "📏 снимаю текст...\n"
            "🧠 анализирую ответы..."
        )
    )
    
    try:
        # Extract content based on file type
        content = await _extract_content(message)
        
        if not content or not content.strip():
            await processing_msg.edit_text(
                text=(
                    f"❌ Не удалось получить текст\n\n"
                    f"Используйте:\n"
                    f"• Прасные фото с четким текстом\n"
                    f"• PDF, DOCX с текством\n"
                    f"• Простые текстовые сообщения"
                ),
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Initialize LLM service
        settings = get_settings()
        llm = ReplicateClient(
            api_token=settings.REPLICATE_API_TOKEN,
            model=settings.REPLICATE_MODEL
        )
        checker = HomeworkChecker(llm)
        
        # Check homework
        result = await checker.check_homework(
            content=content,
            subject=subject_code
        )
        
        # Format result
        result_text = ResultVisualizer.format_result(result)
        
        # Update message with result
        await processing_msg.edit_text(text=result_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error processing homework: {e}")
        await processing_msg.edit_text(
            text=(
                f"❌ Ошибка при анализе:\n"
                f"<code>{str(e)}</code>"
            ),
            parse_mode="HTML"
        )
    
    # Reset state
    await state.clear()


async def _extract_content(message: Message) -> str:
    """Extract content from message.
    
    Args:
        message: Message with file or text
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If content cannot be extracted
    """
    # Handle text message
    if message.text:
        return message.text
    
    # Handle photo with OCR
    if message.photo:
        return await _extract_text_from_photo(message)
    
    # Handle document
    if message.document:
        return await _extract_text_from_document(message)
    
    raise ValueError("Неподдерживаемый тип содержимого")


async def _extract_text_from_photo(message: Message) -> str:
    """Extract text from photo using LLM vision (OCR).
    
    Args:
        message: Message with photo
        
    Returns:
        Extracted text
    """
    try:
        # Get the largest photo available
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Download photo to memory
        settings = get_settings()
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        
        try:
            # Read image and convert to base64 for vision API
            with open(temp_file, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Use LLM vision to extract text from image
            settings = get_settings()
            llm = ReplicateClient(
                api_token=settings.REPLICATE_API_TOKEN,
                model=settings.REPLICATE_MODEL
            )
            
            # Create OCR prompt
            ocr_prompt = (
                "Опиши все текстовое содержимое в этом изображении.\n"
                "Выдели все цифры, выражения, формулы.\n"
                "Отвечай ТОЛЬКО на РУССКОМ языке!"
            )
            
            # Call LLM for OCR
            extracted_text = await llm.analyze_document(
                document_text="[ФОТО]",
                user_prompt=ocr_prompt
            )
            
            logger.info(f"Extracted {len(extracted_text)} chars from photo using LLM vision")
            return extracted_text
        
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    except Exception as e:
        logger.warning(f"Failed to extract text from photo: {e}")
        # Return caption if available as fallback
        if message.caption:
            return message.caption
        return ""


async def _extract_text_from_document(message: Message) -> str:
    """Extract text from document file.
    
    Args:
        message: Message with document
        
    Returns:
        Extracted text
    """
    # Download file
    settings = get_settings()
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(exist_ok=True)
    
    file_info = await message.bot.get_file(message.document.file_id)
    file_path = temp_dir / message.document.file_name
    
    # Download and save
    await message.bot.download_file(file_info.file_path, file_path)
    
    try:
        # Process based on file type
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
            raise ValueError(f"Неподдерживаемый тип файла: {message.document.mime_type}")
    
    finally:
        # Clean up
        if file_path.exists():
            file_path.unlink()
    
    return content
