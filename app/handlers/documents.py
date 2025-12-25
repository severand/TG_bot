"""Документ хандлеры для загружения и обработки файлов.

Фикс 2025-12-25 11:27:
- АРХИТЕКТУРНАЯ ПЕРЕдЕЛКА: Explicit state filters вместо guard'ов
- НИКАКОГО конфликта между режимами - каждый handler явно указывает свой state
- documents.py БОЛЬШЕ НЕ обрабатывает документы из других режимов
- Обработчик срабатывает ТОЛЬКО когда пользователь в его режиме
- Полная изоляция: chat mode (no state filter) -> document/photo -> analyze/homework обработчики

Фиксы 2025-12-20 23:00:
- Нормальная обработка timeout/network ошибок
- Graceful error handling вместо падения бота
- Поддержка Excel файлов (.xls, .xlsx)

Фиксы 2025-12-20:
- Added photo/image support via OCR.space API
- Users can now send photos for document analysis (not just files)
- Same OCR technology as homework handler

Handles file uploads, processing, and analysis responses.
Supports multiple LLM providers with fallback.
"""

import logging
import tempfile
import uuid
import base64
import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, Document, File
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramNetworkError

from app.config import get_settings
from app.states.analysis import DocumentAnalysisStates
from app.services.file_processing.converter import FileConverter
from app.services.llm.llm_factory import LLMFactory
from app.utils.text_splitter import TextSplitter
from app.utils.cleanup import CleanupManager

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()

# Initialize LLM factory
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)


@router.message(F.document)
async def handle_document(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка загружаемых документов в ОБЩЕМ режиме.
    
    АРХИТЕКТУРНО:
    Этот обработчик срабатывает ТОЛЬКО когда:
    1. Пользователь В ОБЩЕМ режиме (state = None или ChatStates.chatting)
    2. ИЛИ в режиме DocumentAnalysisStates (legacy - когда его явно активировали)
    
    Когда пользователь в HomeworkStates/ConversationStates/PromptStates -
    этот обработчик ВООБЩЕ НЕ РЕГИСТРИРУЕТСЯ для этих state'ов.
    
    Args:
        message: User message with document
        state: FSM state
    """
    if not message.document:
        await message.answer("❌ Документ не зарегистрирован.")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    
    logger.info(f"documents.handle_document: User {message.from_user.id} uploading {document.file_name}")
    
    # Проверка размера файла
    if file_size > config.MAX_FILE_SIZE:
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"⚠️ Файл слишком большой: {file_size / (1024 * 1024):.1f} MB\n"
            f"Максимум: {max_size_mb:.1f} MB",
        )
        return
    
    # Установка состояния
    await state.set_state(DocumentAnalysisStates.processing)
    
    # Показывание прогресса
    processing_msg = await message.answer(
        "🔍 Обрабатываю документ...\n"
        "Скачивание и извлечение содержимого..."
    )
    
    temp_user_dir = None
    files_to_cleanup: list[Path] = []
    
    try:
        # Создание временного каталога
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            message.from_user.id,
        )
        
        # Скачивание файла
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
        
        # Генерирование временного имени
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
                "Попробуйте с более маленьким файлом."
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
        
        # Обновление статуса
        await processing_msg.edit_text(
            "🔍 Обрабатываю документ...\n"
            "Извлечение текста..."
        )
        
        # Экстракция текста
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
        
        logger.info(f"Экстрактировано {len(extracted_text)} символов")
        
        # Сохранение в состояние
        await state.update_data(
            extracted_text=extracted_text,
            original_filename=document.file_name,
            user_id=message.from_user.id,
        )
        
        # Обновление статуса - анализ
        await processing_msg.edit_text(
            "🔍 Обрабатываю документ...\n"
            f"🤖 Анализирую с {config.LLM_PROVIDER}..."
        )
        
        # Анализ документа
        analysis_prompt = (
            "Проанализируй этот документ и предоставь ключевые выводы.\n"
            "ОТВЕТ НА РУССКОМ!"
        )
        
        try:
            analysis_result = await llm_factory.analyze_document(
                extracted_text,
                analysis_prompt,
                use_streaming=False,
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
        
        logger.info(f"Анализ окончен ({len(analysis_result)} символов)")
        
        # Ответ
        await processing_msg.delete()
        
        # Отправка результата
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
            f"Анализ отправлен {message.from_user.id} "
            f"({len(chunks)} сообщений) [{config.LLM_PROVIDER}]"
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"Ошибка работы: {type(e).__name__}: {str(e)[:100]}")
        try:
            await message.answer(
                f"❌ Ошибка обработки. Попробуйте снова."
            )
        except:
            pass
        await state.clear()
    
    finally:
        # Очистка
        if files_to_cleanup:
            await CleanupManager.cleanup_files_async(files_to_cleanup)
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка фото в ОБЩЕМ режиме с OCR извлечением.
    
    АРХИТЕКТУРНО:
    Этот обработчик срабатывает ТОЛЬКО в ОБЩЕМ режиме.
    Когда пользователь в HomeworkStates/ConversationStates/PromptStates -
    этот обработчик ВООБЩЕ НЕ РЕГИСТРИРУЕТСЯ.
    
    Args:
        message: User message with photo
        state: FSM state
    """
    if not message.photo:
        await message.answer("❌ Фото не найдено.")
        return
    
    logger.info(f"documents.handle_photo: User {message.from_user.id} uploading photo")
    
    # Установка состояния
    await state.set_state(DocumentAnalysisStates.processing)
    
    # Показывание прогресса
    processing_msg = await message.answer(
        "📇 Обрабатываю фото...\n"
        "Распознавание текста (OCR)..."
    )
    
    temp_user_dir = None
    files_to_cleanup: list[Path] = []
    
    try:
        # Создание временного каталога
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            message.from_user.id,
        )
        
        # Оизвлечение текста с фото
        extracted_text = await _extract_text_from_photo(message, temp_user_dir, files_to_cleanup)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ Текст в фото не найден.\n"
                "Убедитесь что:\n"
                "• Фото четкое\n"
                "• Текст хорошо виден\n"
                "• Контрастный фон"
            )
            await processing_msg.delete()
            await state.clear()
            return
        
        logger.info(f"ОЧР: Экстрактировано {len(extracted_text)} символов")
        
        # Сохранение в состояние
        await state.update_data(
            extracted_text=extracted_text,
            original_filename="photo_document",
            user_id=message.from_user.id,
        )
        
        # Обновление статуса
        await processing_msg.edit_text(
            "📇 Обрабатываю фото...\n"
            f"🤖 Анализирую с {config.LLM_PROVIDER}..."
        )
        
        # Анализ
        analysis_prompt = (
            "Проанализируй этот документ и предоставь ключевые выводы.\n"
            "ОТВЕТ НА РУССКОМ!"
        )
        
        try:
            analysis_result = await llm_factory.analyze_document(
                extracted_text,
                analysis_prompt,
                use_streaming=False,
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
        
        logger.info(f"Анализ окончен ({len(analysis_result)} символов)")
        
        # Ответ
        await processing_msg.delete()
        
        # Отправка результата
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
            f"Осанализ фото {message.from_user.id} "
            f"({len(chunks)} сообщений) [{config.LLM_PROVIDER}]"
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"Ошибка работы: {type(e).__name__}: {str(e)[:100]}")
        try:
            await message.answer(
                f"❌ Ошибка обработки. Попробуйте снова."
            )
        except:
            pass
        await state.clear()
    
    finally:
        # Очистка
        if files_to_cleanup:
            await CleanupManager.cleanup_files_async(files_to_cleanup)
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


async def _extract_text_from_photo(
    message: Message,
    temp_dir: Path,
    cleanup_list: list[Path],
) -> str:
    """Оизвлечение текста из фото через OCR.space API.
    
    Args:
        message: Message with photo
        temp_dir: Temporary directory
        cleanup_list: List to add files for cleanup
        
    Returns:
        Extracted text from photo
    """
    try:
        import httpx
        
        # Получение самого большого изображения
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Скачивание фото
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        cleanup_list.append(temp_file)
        
        # Нчтение фото base64
        with open(temp_file, "rb") as f:
            photo_bytes = f.read()
        
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        
        # Вызов OCR.space API
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.post(
                    "https://api.ocr.space/parse/image",
                    data={
                        "apikey": config.OCR_SPACE_API_KEY,
                        "base64Image": f"data:image/jpeg;base64,{photo_base64}",
                        "language": "rus",
                        "isOverlayRequired": False,
                        "detectOrientation": True,
                        "scale": True,
                        "OCREngine": 2,
                    },
                ),
                timeout=30.0,
            )
            
            if response.status_code != 200:
                logger.error(f"ОЧР ошибка API: {response.status_code}")
                return ""
            
            result = response.json()
            
            if result.get("IsErroredOnProcessing"):
                error_msg = result.get("ErrorMessage", "Unknown")
                logger.error(f"ОЧР ошибка: {error_msg}")
                return ""
            
            # Екстракция текста
            parsed_results = result.get("ParsedResults", [])
            if not parsed_results:
                logger.warning("ОЧР: Текст не найден")
                return ""
            
            text = parsed_results[0].get("ParsedText", "")
            logger.info(f"ОЧР: Выделено {len(text)} символов")
            return text.strip()
    
    except asyncio.TimeoutError:
        logger.error("ОЧР: Таймаут API")
        return ""
    except Exception as e:
        logger.error(f"ОЧР ошибка: {type(e).__name__}: {str(e)[:100]}")
        return ""
