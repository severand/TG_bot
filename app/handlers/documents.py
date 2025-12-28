"""Документ хандлеры для загружения и обработки файлов.

Handles file uploads, processing, and analysis responses.
Supports multiple LLM providers with fallback.

UPDATED 2025-12-28 23:10:
- REPLACED: OCR.space API → LOCAL Tesseract/EasyOCR (no SSL issues!)
- ADDED: Unified OCR Service across all modes
- FIXED: JPG recognition now works in all modes
- IMPROVED: Quality assessment for OCR results

UPDATED 2025-12-25 14:45:
- УДАЛЕНы дубли логирования текстов и промптов
- Все логирование теперь в replicate_client.py
"""

import logging
import tempfile
import uuid
import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, Document, File
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.filters import StateFilter
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramNetworkError

from app.config import get_settings
from app.states.analysis import DocumentAnalysisStates
from app.states.homework import HomeworkStates
from app.states.conversation import ConversationStates
from app.states.prompts import PromptStates
from app.services.file_processing.converter import FileConverter
from app.services.llm.llm_factory import LLMFactory
from app.services.ocr import OCRService, OCRQualityLevel
from app.utils.text_splitter import TextSplitter
from app.utils.cleanup import CleanupManager

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()
ocr_service = OCRService()

llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)


@router.message(
    F.document,
    ~StateFilter(HomeworkStates, ConversationStates, PromptStates),
)
async def handle_document(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка документов в ОБЩЕМ режиме.
    
    Args:
        message: User message with document
        state: FSM state
    """
    current_state = await state.get_state()
    user_id = message.from_user.id
    
    logger.debug(f"[DOCUMENTS DEBUG] User {user_id}: handle_document called")
    logger.debug(f"[DOCUMENTS DEBUG] User {user_id}: Current state: {current_state}")
    
    if not message.document:
        await message.answer("❌ Документ не зарегистрирован.")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    
    logger.info(f"documents.handle_document: User {user_id} uploading {document.file_name}")
    
    if file_size > config.MAX_FILE_SIZE:
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"⚠️ Файл слишком большой: {file_size / (1024 * 1024):.1f} MB\n"
            f"Максимум: {max_size_mb:.1f} MB",
        )
        return
    
    await state.set_state(DocumentAnalysisStates.processing)
    
    processing_msg = await message.answer(
        "🔍 Обрабатываю документ...\n"
        "Скачивание и извлечение содержимого..."
    )
    
    temp_user_dir = None
    files_to_cleanup: list[Path] = []
    
    try:
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            user_id,
        )
        
        bot = message.bot
        try:
            file: File = await asyncio.wait_for(
                bot.get_file(document.file_id),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting file info for {document.file_name}")
            await message.answer(
                "⚠️ Таймаут при скачивании файла.\n"
                "Попробуйте позже или отправьте другой файл."
            )
            await processing_msg.delete()
            await state.clear()
            return
        except TelegramNetworkError as e:
            logger.error(f"Network error getting file: {e}")
            await message.answer(
                "⚠️ Ошибка сети при скачивании.\n"
                "Проверьте интернет и попробуйте снова."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        if not file.file_path:
            await message.answer("❌ Не удалось получить путь к файлу.")
            await processing_msg.delete()
            await state.clear()
            return
        
        file_ext = Path(document.file_name or "document").suffix or ".bin"
        temp_file_path = temp_user_dir / f"{uuid.uuid4()}{file_ext}"
        files_to_cleanup.append(temp_file_path)
        
        try:
            await asyncio.wait_for(
                bot.download_file(file.file_path, temp_file_path),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading file {document.file_name}")
            await message.answer(
                "⚠️ Таймаут при скачивании файла.\n"
                "Попробуйте с более малым файлом."
            )
            await processing_msg.delete()
            await state.clear()
            return
        except TelegramNetworkError as e:
            logger.error(f"Network error downloading file: {e}")
            await message.answer(
                "⚠️ Ошибка сети при скачивании.\n"
                "Проверьте интернет и попробуйте снова."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"Загружен файл: {temp_file_path.name} ({file_size} bytes)")
        
        await processing_msg.edit_text(
            "🔍 Обрабатываю документ...\n"
            "Обработка содержимого..."
        )
        
        try:
            converter = FileConverter()
            extracted_text = converter.extract_text(temp_file_path, temp_user_dir)
        except ValueError as e:
            logger.error(f"Ошибка формата: {e}")
            await message.answer(
                f"⚠️ Нет поддержки этого формата.\n"
                f"Поддерживаются: PDF, DOCX, TXT, Excel, ZIP, DOC"
            )
            await processing_msg.delete()
            await state.clear()
            return
        except Exception as e:
            logger.error(f"Ошибка извлечения: {type(e).__name__}: {str(e)[:100]}")
            await message.answer(
                f"⚠️ Ошибка при извлечении текста.\n"
                f"Попробуйте другой файл."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ В документе не найден текст.\n"
                "Попробуйте другой файл."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"Document extracted {len(extracted_text)} chars for user {user_id}")
        
        await state.update_data(
            extracted_text=extracted_text,
            original_filename=document.file_name,
            user_id=user_id,
        )
        
        await processing_msg.edit_text(
            "🔍 Обрабатываю документ...\n"
            f"🤖 Анализирую с {config.LLM_PROVIDER}..."
        )
        
        analysis_prompt = (
            "Проанализируй этот документ и предоставь ключевые выводы.\n"
            "ОТВЕТ НА РУССКОМ!"
        )
        
        system_prompt = (
            "Ты внимательный аналитик. "
            "Помоги разбераться в материалах документа."
        )
        
        try:
            analysis_result = await llm_factory.analyze_document(
                extracted_text,
                analysis_prompt,
                system_prompt=system_prompt,
                use_streaming=False,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Ошибка ЛЛМ: {type(e).__name__}: {str(e)[:100]}")
            await message.answer(
                f"⚠️ Ошибка анализа: {str(e)[:80]}"
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        if not analysis_result:
            await message.answer(
                "❌ Анализ не удался. Попробуйте снова."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"Analysis completed ({len(analysis_result)} chars) for user {user_id}")
        
        await processing_msg.delete()
        
        splitter = TextSplitter()
        chunks = splitter.split(analysis_result)
        
        for i, chunk in enumerate(chunks, 1):
            prefix = f"*[Часть {i}/{len(chunks)}]*\n\n" if len(chunks) > 1 else ""
            try:
                await message.answer(
                    f"{prefix}{chunk}",
                    parse_mode="Markdown",
                )
            except TelegramNetworkError as e:
                logger.error(f"Ошибка сети при отправке: {e}")
                continue
        
        logger.info(
            f"Analysis sent to {user_id} "
            f"({len(chunks)} messages) [{config.LLM_PROVIDER}]"
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in handle_document: {type(e).__name__}: {str(e)[:100]}")
        try:
            await message.answer(
                f"❌ Ошибка обработки. Попробуйте снова."
            )
        except:
            pass
        await state.clear()
    
    finally:
        if files_to_cleanup:
            await CleanupManager.cleanup_files_async(files_to_cleanup)
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(
    F.photo,
    ~StateFilter(HomeworkStates, ConversationStates, PromptStates),
)
async def handle_photo(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка фото в ОБЩЕМ режиме с LOCAL OCR.
    
    Args:
        message: User message with photo
        state: FSM state
    """
    current_state = await state.get_state()
    user_id = message.from_user.id
    
    logger.debug(f"[DOCUMENTS DEBUG] User {user_id}: handle_photo called")
    logger.debug(f"[DOCUMENTS DEBUG] User {user_id}: Current state: {current_state}")
    
    if not message.photo:
        await message.answer("❌ Фото не найдено.")
        return
    
    logger.info(f"documents.handle_photo: User {user_id} uploading photo")
    
    await state.set_state(DocumentAnalysisStates.processing)
    
    processing_msg = await message.answer(
        "📗 Обрабатываю фото...\n"
        "Распознавание текста (OCR)..."
    )
    
    temp_user_dir = None
    files_to_cleanup: list[Path] = []
    
    try:
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            user_id,
        )
        
        # Download photo
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        temp_file = temp_user_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        files_to_cleanup.append(temp_file)
        
        logger.info(f"Downloaded photo: {temp_file}")
        
        # Extract text using unified OCR service
        extracted_text, quality = await ocr_service.extract_from_file(temp_file, user_id)
        
        logger.info(
            f"[OCR QUALITY] User {user_id}: {quality.value} | "
            f"{len(extracted_text)} chars, {len(extracted_text.split())} words"
        )
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ Текст в фото не найден.\n"
                "Убедитесь что:\n"
                "• Фото четкое\n"
                "• Текст хорошо виден\n"
                "• Контрастный фон\n\n"
                "*⚠️ ВАЖНО:* Рукописный текст может распознаться неверно. "
                "Используйте PDF или четкие фото печатного текста."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        if quality == OCRQualityLevel.POOR:
            await message.answer(
                "⚠️ КАЧЕСТВО OCR: Низкое\n"
                "Можно сложная рукопись или низкая текстура источника."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"OCR extracted {len(extracted_text)} chars for user {user_id}")
        
        await state.update_data(
            extracted_text=extracted_text,
            original_filename="photo_document",
            user_id=user_id,
        )
        
        await processing_msg.edit_text(
            "📗 Обрабатываю фото...\n"
            f"🤖 Анализирую с {config.LLM_PROVIDER}..."
        )
        
        analysis_prompt = (
            "Проанализируй этот документ и предоставь ключевые выводы.\n"
            "ОТВЕТ НА РУССКОМ!"
        )
        
        system_prompt = (
            "Ты внимательный аналитик. "
            "Помоги разбераться в материалах фото."
        )
        
        try:
            analysis_result = await llm_factory.analyze_document(
                extracted_text,
                analysis_prompt,
                system_prompt=system_prompt,
                use_streaming=False,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Ошибка ЛЛМ: {type(e).__name__}: {str(e)[:100]}")
            await message.answer(
                f"⚠️ Ошибка анализа: {str(e)[:80]}"
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        if not analysis_result:
            await message.answer(
                "❌ Анализ не удался. Попробуйте снова."
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"Analysis completed ({len(analysis_result)} chars) for user {user_id}")
        
        await processing_msg.delete()
        
        splitter = TextSplitter()
        chunks = splitter.split(analysis_result)
        
        for i, chunk in enumerate(chunks, 1):
            prefix = f"*[Часть {i}/{len(chunks)}]*\n\n" if len(chunks) > 1 else ""
            try:
                await message.answer(
                    f"{prefix}{chunk}",
                    parse_mode="Markdown",
                )
            except TelegramNetworkError as e:
                logger.error(f"Ошибка сети при отправке: {e}")
                continue
        
        logger.info(
            f"Photo analysis sent to {user_id} "
            f"({len(chunks)} messages) [{config.LLM_PROVIDER}]"
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in handle_photo: {type(e).__name__}: {str(e)[:100]}")
        try:
            await message.answer(
                f"❌ Ошибка. Попробуйте снова."
            )
        except:
            pass
        await state.clear()
    
    finally:
        if files_to_cleanup:
            await CleanupManager.cleanup_files_async(files_to_cleanup)
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)
