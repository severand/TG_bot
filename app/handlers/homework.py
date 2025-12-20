"""Homework checking handler.

Handles /homework command for checking student homework.
OCR: Uses LLaVA vision model to extract text from photos.
"""

import logging
from typing import Optional
from pathlib import Path
import httpx

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
            f"📄 Отправьте:\n"
            f"• Текстовое сообщение\n"
            f"• PDF или DOCX файл\n"
            f"• Фото (распознается автоматически)"
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
                    f"💡 Пробуюте:\n"
                    f"• Отправьте текст выче\n"
                    f"• Отослите решение текстом\n"
                    f"• Отослите высоки качество фото с четким текстом"
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
    
    Handles:
    - Text messages (direct text)
    - PDF/DOCX files (extract text)
    - Photos (OCR via LLaVA vision model)
    
    Args:
        message: Message with file or text
        
    Returns:
        Extracted text content
    """
    # Handle text message
    if message.text:
        return message.text
    
    # Handle photo - use LLaVA OCR
    if message.photo:
        return await _extract_text_from_photo(message)
    
    # Handle document
    if message.document:
        return await _extract_text_from_document(message)
    
    raise ValueError("Неподдерживаемый тип содержимого")


async def _extract_text_from_photo(message: Message) -> str:
    """Extract text from photo using LLaVA vision model (OCR).
    
    Steps:
    1. Download photo from Telegram
    2. Upload to temporary URL accessible by Replicate
    3. Call LLaVA model with OCR prompt
    4. Return extracted text
    
    Args:
        message: Message with photo
        
    Returns:
        Extracted text from photo
    """
    try:
        # Get the largest photo
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Download photo
        settings = get_settings()
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        
        try:
            # Read photo bytes
            with open(temp_file, "rb") as f:
                photo_bytes = f.read()
            
            # Get Replicate API token
            settings = get_settings()
            api_token = settings.REPLICATE_API_TOKEN
            
            # Call LLaVA vision model directly via Replicate API
            # Using the correct model version
            extracted_text = await _call_llava_ocr(
                photo_bytes=photo_bytes,
                api_token=api_token
            )
            
            logger.info(f"OCR: Extracted {len(extracted_text)} chars from photo")
            return extracted_text
        
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    except Exception as e:
        logger.error(f"Failed to extract text from photo via OCR: {e}")
        return ""


async def _call_llava_ocr(photo_bytes: bytes, api_token: str) -> str:
    """Call LLaVA vision model for OCR via Replicate API.
    
    Uses streaming to get text extraction results.
    
    Args:
        photo_bytes: Photo file bytes
        api_token: Replicate API token
        
    Returns:
        Extracted text
    """
    import base64
    import json
    
    # Encode photo as base64
    photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
    photo_data_uri = f"data:image/jpeg;base64,{photo_base64}"
    
    # Prepare request to Replicate API
    # Using LLaVA v1.6 Mistral 7B (more efficient)
    model_version = "19be067b589d0c46689ffa7cc3ff321447a441986a7694c01225973c2eafc874"
    
    prompt = (
        "Опиши ВЕСЬ текст на этом изображении.\n"
        "Выпиши каждое слово так как оно написано.\n"
        "Ответ ТОЛЬКО на русском языке!"
    )
    
    payload = {
        "image": photo_data_uri,
        "prompt": prompt,
    }
    
    # Call Replicate API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.replicate.com/v1/predictions",
                json={
                    "version": model_version,
                    "input": payload,
                },
                headers={"Authorization": f"Token {api_token}"},
                timeout=60.0,
            )
            
            if response.status_code != 201:
                raise Exception(f"Replicate API error: {response.status_code} {response.text}")
            
            prediction = response.json()
            prediction_id = prediction.get("id")
            
            # Poll for result
            max_attempts = 30  # 30 seconds max wait
            for attempt in range(max_attempts):
                result_response = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {api_token}"},
                    timeout=10.0,
                )
                
                result_data = result_response.json()
                status = result_data.get("status")
                
                if status == "succeeded":
                    output = result_data.get("output", "")
                    # Output might be a list or string
                    if isinstance(output, list):
                        return "".join(output)
                    return str(output)
                
                elif status == "failed":
                    error = result_data.get("error", "Unknown error")
                    raise Exception(f"Prediction failed: {error}")
                
                # Wait before next poll
                import asyncio
                await asyncio.sleep(1)
            
            raise Exception("Timeout waiting for OCR result")
        
        except Exception as e:
            logger.error(f"LLaVA OCR error: {e}")
            raise


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
