"""Homework checking handler.

Handles /homework command for checking student homework.
"""

import logging
from typing import Optional
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, File
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.filters.content_types import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.session import aiohttp_session

from app.states.homework import HomeworkStates
from app.services.homework import HomeworkChecker, SubjectCheckers, ResultVisualizer
from app.services.llm.replicate_service import ReplicateService
from app.services.file_processing.pdf_processor import process_pdf
from app.services.file_processing.image_processor import process_image
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
            f"📄 Отправь ссылку или файл"
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
    """Process homework file or text.
    
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
            "✏️ снимаю текст...\n"
            🧠 анализирую ответы..."
        )
    )
    
    try:
        # Extract content based on file type
        content = await _extract_content(message)
        
        # Initialize LLM service
        settings = get_settings()
        llm = ReplicateService(api_key=settings.REPLICATE_API_KEY)
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
    
    # Handle photo
    if message.photo:
        logger.warning("Photo processing not yet implemented, using caption")
        return message.caption or "[Photo uploaded without text]"
    
    # Handle document
    if message.document:
        # Download file
        settings = get_settings()
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(exist_ok=True)
        
        file_info = await message.bot.get_file(message.document.file_id)
        file_path = temp_dir / message.document.file_name
        
        # Download and save
        await message.bot.download_file(file_info.file_path, file_path)
        
        # Process based on file type
        if message.document.mime_type == "application/pdf":
            content = process_pdf(str(file_path))
        elif message.document.mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            try:
                from docx import Document
                doc = Document(file_path)
                content = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                logger.error(f"Error processing DOCX: {e}")
                raise ValueError("Cannot read DOCX file")
        elif message.document.mime_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            raise ValueError(f"Unsupported file type: {message.document.mime_type}")
        
        # Clean up
        file_path.unlink()
        
        return content
    
    raise ValueError("Unsupported content type")
