"""Конверсация моде хандлеры для анализа документов.

POLNAYA PODDERZHKA:
- Word: .docx, .doc
- Excel: .xlsx, .xls  
- PDF
- Text: .txt
- Images: .jpg, .png (OCR)

UPDATED 2025-12-28 20:57:
- REMOVED format restrictions
- Support ALL formats via openpyxl + pandas
- Graceful error handling only on actual failures

UPDATED 2025-12-25 14:48:
- Added user_id parameter to analyze_document calls
- All logging now includes user context

Fixes 2025-12-25 11:27:
- АРХИТЕКТУРНАЯ ОПТИМизация: ЭКСПЛИЦИТНЫЕ state filters в декораторах
- Обработчики срабатывают ТОЛЬКО когда пользователь В ConversationStates.ready
- В других режимах (домашка, промпты) документы обрабатываются специализированными обработчиками
- НИКАКОГО конфликта между режимами вовле

Handles document analysis and user prompts for interactive conversation.
"""

import logging
import uuid
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document, File, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.states.conversation import ConversationStates
from app.services.file_processing.converter import FileConverter
from app.services.llm.llm_factory import LLMFactory
from app.services.prompts.prompt_manager import PromptManager
from app.utils.text_splitter import TextSplitter
from app.utils.cleanup import CleanupManager

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()
prompt_manager = PromptManager()
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)


def _get_prompts_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Получить клавиатуру с ONLY документными анализ промптами - 2 кнопки в строке.
    
    КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Используем get_prompt_by_category() для получения
    ТОЛЬКО промптов категории "document_analysis", а НЕ всех промптов.
    """
    # Лоадим промпты пользователя
    prompt_manager.load_user_prompts(user_id)
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО промпты для документных промптов
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    logger.debug(f"User {user_id}: Loading {len(prompts)} DOCUMENT ANALYSIS prompts")
    
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки только для документных промптов
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        button_text = f"{prompt.description[:40]}"
        builder.button(
            text=button_text,
            callback_data=f"analyze_select_prompt_{name}"
        )
    
    # Кнопка отмены
    builder.button(text="« Отмена", callback_data="analyze_cancel")
    builder.adjust(2)  # 2 кнопки в ряду
    
    return builder.as_markup()


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    """Активировать режим анализа документов - теперь с выбором промпта."""
    logger.info(f"User {message.from_user.id} activated /analyze")
    await start_analyze_mode(message=message, state=state)


async def start_analyze_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Начать интерактивный режим анализа документов.
    
    NEW: Показывать выбор промпта В ПЕРВЫХ, то вапросию для документа.
    ТОЛЬКО промпты для анализа документов!
    """
    if state is None:
        logger.error("state is None in start_analyze_mode")
        return
    
    user_id = message.from_user.id if message else callback.from_user.id if callback else None
    
    if not user_id:
        logger.error("Cannot determine user_id")
        return
    
    # Load user prompts
    prompt_manager.load_user_prompts(user_id)
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО документные промпты
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    await state.set_state(ConversationStates.selecting_prompt)
    
    text = (
        "📓 *Анализ документов*\n\n"
        "Шаг 1★1★1 из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов анализа*\n\n"
        "🔙 *ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ:*\n"
        "• Word: .docx, **.doc** (СТАРЫЙ)\n"
        "• Excel: .xlsx, **.xls** (СТАРЫЙ)\n"
        "• ПДФ: PDF\n"
        "• ТЕКСТ: TXT\n"
        "• ФОТО: JPG, PNG (OCR текста)\n"
        "• АРХИВЫ: ZIP\n\n"
        "🌟 *ВсЕ форматы работают!*\n\n"
        "🔙 *Как это работает:*\n"
        "1★1★1 Выберите промпт\n"
        "2★1★1 Отправьте документ (ANY FORMAT)\n"
        "3★1★1 Получите результат\n\n"
        "📄 *ОТПРАВТЕ ВЕЩЬ (ЛЮБОЕ):*\n"
        "• .doc, .docx, .xls, .xlsx, .pdf, .txt\n"
        "• Фото документа (jpg, png)\n"
        "• ZIP архивы\n\n"
        "👇 Выберите тип анализа:"
    )
    
    if message:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        logger.info(f"Analysis mode started for user {user_id} with {len(prompts)} document prompts")
    elif callback:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        await callback.answer()
        logger.info(f"Analysis mode started for user {user_id} with {len(prompts)} document prompts")


@router.callback_query(F.data.startswith("analyze_select_prompt_"))
async def cb_select_prompt(query: CallbackQuery, state: FSMContext) -> None:
    """Обработать выбор промпта - перейти в состояние загружки документа."""
    prompt_name = query.data.replace("analyze_select_prompt_", "")
    user_id = query.from_user.id
    
    # Verify prompt exists
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    if not prompt:
        await query.answer("❌ Промпт не найден", show_alert=True)
        return
    
    # Save prompt to state
    await state.update_data(selected_prompt_name=prompt_name)
    
    # Move to document upload state
    await state.set_state(ConversationStates.ready)
    
    logger.info(f"User {user_id} selected prompt: {prompt_name}")
    
    text = (
        f"✅ *Промпт выбран!*\n\n"
        f"📄 *Тип анализа:* `{prompt_name}`\n"
        f"_{prompt.description}_\n\n"
        f"📂 *Шаг 2★1★1 из 2:* Отправьте документ\n\n"
        f"🌟 *ПОДДЕРЖИВАЕМЫЕ:*\n"
        f".doc, .docx, .xls, .xlsx, .pdf, .txt, images (OCR), ZIP\n\n"
        f"📁 Отправьте ЛЮБОЙ файл!"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="analyze_back_to_prompts")]]
        ),
    )
    
    await query.answer()


@router.callback_query(F.data == "analyze_back_to_prompts")
async def cb_back_to_prompts(query: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к выбору промпта."""
    user_id = query.from_user.id
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО документные промпты
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    text = (
        "📓 *Анализ документов*\n\n"
        "Шаг 1★1★1 из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов*\n\n"
        "🌟 *ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ:*\n"
        ".doc, .docx, .xls, .xlsx, .pdf, .txt, images, ZIP\n\n"
        "👇 Выберите тип анализа:"
    )
    
    await state.set_state(ConversationStates.selecting_prompt)
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=_get_prompts_keyboard(user_id),
    )
    await query.answer()


@router.callback_query(F.data == "analyze_cancel")
async def cb_analyze_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Отменить режим анализа."""
    await state.clear()
    
    text = "❌ *Отменено*\n\nВозвращаемся в режим диалога."
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} cancelled analyze mode")


@router.message(
    ConversationStates.ready,
    F.document
)
async def handle_document_upload(message: Message, state: FSMContext) -> None:
    """Обработка загруженного документа.
    
    ПОДДЕРЖИВАЕТ ВСЕ ФОРМАТЫ:
    - .doc, .docx (Word)
    - .xls, .xlsx (Excel)
    - .pdf (PDF)
    - .txt (Text)
    - images (JPG, PNG - OCR)
    - .zip (Archives)
    
    АРХИТЕКТУРНО:
    Этот обработчик срабатывает ТОЛЬКО когда:
    1. Пользователь точно в ConversationStates.ready
    2. Фильтр в декораторе гарантирует это
    """
    if not message.document:
        await message.answer("❌ Документ не найден")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    file_name = document.file_name or "document"
    
    logger.info(f"User {message.from_user.id} uploading document: {file_name} ({file_size} bytes)")
    
    # Validate file size
    if file_size > config.MAX_FILE_SIZE:
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"⚠️ Файл слишком большой: {file_size / (1024 * 1024):.1f} MB\n"
            f"Максимум: {max_size_mb:.1f} MB"
        )
        return
    
    # Show processing
    status_msg = await message.answer(
        "🔍 Обрабатываю документ...\n"
        "Скачивание и извлечение текста..."
    )
    
    file_uuid = str(uuid.uuid4())
    temp_user_dir = None
    
    try:
        # Create UNIQUE temp directory для этого файла
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        
        unique_temp_name = f"{message.from_user.id}_{file_uuid}"
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            unique_temp_name,
        )
        
        # Download file
        bot = message.bot
        file: File = await bot.get_file(document.file_id)
        
        if not file.file_path:
            await message.answer("❌ Не удалось получить путь к файлу")
            await status_msg.delete()
            return
        
        # Generate unique filename
        file_ext = Path(file_name).suffix or ".bin"
        temp_file_path = temp_user_dir / f"{file_uuid}{file_ext}"
        
        await bot.download_file(file.file_path, temp_file_path)
        logger.info(f"Downloaded: {temp_file_path}")
        
        # Extract text
        await status_msg.edit_text(
            "🔍 Обрабатываю (вычисление текста)..."
        )
        
        converter = FileConverter()
        extracted_text = converter.extract_text(temp_file_path, temp_user_dir)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ Текст в документе не найден.\n\n"
                "Если это изображение:\n"
                "• Отправьте фото вместо документа\n\n"
                "Если документ прустой:\n"
                "• Попробуйте другой файл"
            )
            await status_msg.delete()
            return
        
        # Save to state
        await state.update_data(
            document_text=extracted_text,
            document_name=file_name,
            document_size=len(extracted_text),
            user_id=message.from_user.id,
        )
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        logger.info(
            f"Document loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars"
        )
        
        # Update status message with analysis start
        await status_msg.edit_text(
            f"⏳ Анализирую с промптом '{selected_prompt_name}'...\n"
            "Это может занять некоторое время..."
        )
        
        # Immediately start analysis with selected prompt
        await _perform_analysis(message, state, data, status_msg)
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer(
            f"❌ Ошибка обработки:\n`{str(e)[:100]}`\n\n"
            "Попытайтесь с другим файлом.",
            parse_mode="Markdown",
        )
        await status_msg.delete()
    
    finally:
        # Cleanup ONLY this file's directory
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(
    ConversationStates.ready,
    F.photo
)
async def handle_photo_upload(message: Message, state: FSMContext) -> None:
    """Обработка загруженного фото.
    
    АРХИТЕКТУРНО:
    Этот обработчик срабатывает ТОЛЬКО когда:
    1. Пользователь точно в ConversationStates.ready
    2. Фильтр в декораторе гарантирует это
    """
    if not message.photo:
        await message.answer("❌ Фото не найден")
        return
    
    logger.info(f"User {message.from_user.id} uploading photo")
    
    # Show processing ONLY - no confirmation message after
    status_msg = await message.answer(
        "⏳ Обрабатываю фото...\n"
        "Распознавание текста (OCR)..."
    )
    
    file_uuid = str(uuid.uuid4())
    temp_user_dir = None
    
    try:
        # Create UNIQUE temp directory
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        
        unique_temp_name = f"{message.from_user.id}_{file_uuid}"
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            unique_temp_name,
        )
        
        # Extract text from photo using OCR
        extracted_text = await _extract_text_from_photo_for_analysis(message, temp_user_dir)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ Текст в фото не найден.\n"
                "Убедитесь что:\n"
                "• Фото четкое\n"
                "• Текст хорошо виден\n"
                "• Контрастный фон"
            )
            await status_msg.delete()
            return
        
        # Save to state
        await state.update_data(
            document_text=extracted_text,
            document_name="photo_document",
            document_size=len(extracted_text),
            user_id=message.from_user.id,
        )
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        logger.info(
            f"Photo loaded for user {message.from_user.id}: {len(extracted_text)} chars"
        )
        
        # Update status message with analysis start
        await status_msg.edit_text(
            f"⏳ Анализирую с промптом '{selected_prompt_name}'...\n"
            "Это может занять некоторое время..."
        )
        
        # Immediately start analysis with selected prompt
        await _perform_analysis(message, state, data, status_msg)
    
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
        await status_msg.delete()
    
    finally:
        # Cleanup ONLY this photo's directory
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(ConversationStates.ready)
async def handle_text_in_analyze_mode(message: Message, state: FSMContext) -> None:
    """Handle text messages in analyze mode - treat as document content.
    
    IMPORTANT: This handler captures ANY message that isn't document/photo
    in ConversationStates.ready state.
    """
    if not message.text:
        await message.answer("❌ Поддерживаются документы и фото")
        return
    
    logger.info(f"User {message.from_user.id} sent text in analyze mode")
    
    # Treat text as document content
    text_content = message.text.strip()
    
    if len(text_content) < 10:
        await message.answer("⚠️ Текст слишком короткий. Отправьте документ.")
        return
    
    # Show processing
    status_msg = await message.answer(
        "⏳ Анализирую...\n"
        "Это может занять некоторое время..."
    )
    
    try:
        # Save to state
        await state.update_data(
            document_text=text_content,
            document_name="text_input",
            document_size=len(text_content),
            user_id=message.from_user.id,
        )
        
        # Get data from state
        data = await state.get_data()
        
        # Perform analysis
        await _perform_analysis(message, state, data, status_msg)
    
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:80]}")
        await status_msg.delete()


async def _perform_analysis(
    message: Message, 
    state: FSMContext, 
    data: dict,
    status_msg: Message = None,
) -> None:
    """Провести анализ с выбранным промптом. Авто-делете сообщения прогресса после отправки результатов.
    
    IMPORTANT: После завершения анализа, возвращает пользователя в режим чата (очищает состояние).
    Это гарантирует, что они не остаются в режиме анализа.
    """
    document_text = data.get("document_text")
    document_name = data.get("document_name", "document")
    selected_prompt_name = data.get("selected_prompt_name", "default")
    user_id = message.from_user.id
    
    if not document_text:
        await message.answer("⚠️ Документ не загружен.")
        if status_msg:
            await status_msg.delete()
        # Return to chat mode
        await state.clear()
        return
    
    logger.info(f"User {user_id} starting analysis with prompt '{selected_prompt_name}'")
    
    # Show typing
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Get selected prompt
        prompt = prompt_manager.get_prompt(user_id, selected_prompt_name)
        
        if not prompt:
            prompt = prompt_manager.get_prompt(user_id, "default")
        
        if not prompt:
            await message.answer(
                "❌ Промпт не найден"
            )
        
        # Build analysis command
        analysis_command = prompt.user_prompt_template if prompt else "Проанализируй этот документ и предоставь ключевые выводы."
        
        # Analyze with user_id for logging
        analysis_result = await llm_factory.analyze_document(
            document_text,
            analysis_command,
            system_prompt=prompt.system_prompt if prompt else None,
            use_streaming=False,
            user_id=user_id,
        )
        
        if not analysis_result:
            await message.answer("❌ Анализ не удался. Попробуйте еще раз.")
            if status_msg:
                await status_msg.delete()
            # Return to chat mode
            await state.clear()
            return
        
        # Split and send
        splitter = TextSplitter(max_length=4000)
        chunks = splitter.split(analysis_result)
        
        # ОТОБРАЖЕНИЕ: добавляем имя документа на НАЧАЛО
        if len(chunks) == 1:
            # Одно сообщение
            header = f"📄 *Документ:* `{document_name}`\n\n"
            await message.answer(
                f"{header}{analysis_result}",
                parse_mode="Markdown",
            )
        else:
            # Несколько сообщений - заголовком только в первом
            for i, chunk in enumerate(chunks, 1):
                if i == 1:
                    # Первое сообщение с заголовком и номером
                    prefix = f"📄 *Документ:* `{document_name}`\n\n*[Часть {i}/{len(chunks)}]*\n\n"
                else:
                    # Остальные сообщения
                    prefix = f"*[Часть {i}/{len(chunks)}]*\n\n"
                
                await message.answer(
                    f"{prefix}{chunk}",
                    parse_mode="Markdown",
                )
        
        # Delete progress message after results sent
        if status_msg:
            await status_msg.delete()
        
        logger.info(
            f"Analysis completed for user {user_id}: "
            f"{len(analysis_result)} chars in {len(chunks)} parts"
        )
        
        # CRITICAL: Return to chat mode after analysis completes
        logger.info(f"User {user_id} returned to chat mode")
        await state.clear()
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
        if status_msg:
            await status_msg.delete()
        # Return to chat mode even on error
        await state.clear()


async def _extract_text_from_photo_for_analysis(
    message: Message,
    temp_dir: Path,
) -> str:
    """Извлечь текст из фото используя OCR.space cloud API.
    
    Args:
        message: Message with photo
        temp_dir: Temporary directory
        
    Returns:
        Extracted text from photo
    """
    try:
        import httpx
        import base64
        import asyncio
        
        logger.info(f"OCR: Starting extraction for user {message.from_user.id}")
        
        # Get largest photo
        if not message.photo:
            logger.warning("OCR: No photo found in message")
            return ""
        
        photo = message.photo[-1]
        logger.info(f"OCR: Got photo {photo.file_id}, size: {photo.file_size} bytes")
        
        # Get file info
        file_info = await message.bot.get_file(photo.file_id)
        logger.info(f"OCR: File path: {file_info.file_path}")
        
        # Download photo
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        logger.info(f"OCR: Downloading to {temp_file}")
        await message.bot.download_file(file_info.file_path, temp_file)
        logger.info(f"OCR: Downloaded successfully, size: {temp_file.stat().st_size} bytes")
        
        # Read photo as base64
        with open(temp_file, "rb") as f:
            photo_bytes = f.read()
        logger.info(f"OCR: Read {len(photo_bytes)} bytes from file")
        
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        logger.info(f"OCR: Encoded to base64, size: {len(photo_base64)} chars")
        
        # Prepare API payload
        api_key = config.OCR_SPACE_API_KEY
        if not api_key:
            logger.error("OCR: OCR_SPACE_API_KEY not configured")
            return ""
        
        payload = {
            "apikey": api_key,
            "base64Image": f"data:image/jpeg;base64,{photo_base64}",
            "language": "rus",
            "isOverlayRequired": False,
            "detectOrientation": True,
            "scale": True,
            "OCREngine": 2,
        }
        logger.info(f"OCR: Prepared payload, base64 size: {len(payload['base64Image'])} chars")
        
        # Call OCR.space API with proper timeouts
        logger.info("OCR: Calling OCR.space API...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.ocr.space/parse/image",
                data=payload,
                timeout=httpx.Timeout(60.0, connect=30.0),
            )
            
            logger.info(f"OCR: Got response status {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"OCR: API error {response.status_code}: {response.text[:200]}")
                return ""
            
            # Parse response
            try:
                result = response.json()
            except Exception as e:
                logger.error(f"OCR: Failed to parse JSON response: {e}")
                logger.error(f"OCR: Response text: {response.text[:500]}")
                return ""
            
            logger.info(f"OCR: Response keys: {result.keys()}")
            
            # Check for processing errors
            if result.get("IsErroredOnProcessing"):
                error_msg = result.get("ErrorMessage", "Unknown error")
                logger.error(f"OCR: Processing error: {error_msg}")
                return ""
            
            # Extract text from parsed results
            parsed_results = result.get("ParsedResults", [])
            if not parsed_results:
                logger.warning("OCR: No parsed results in response")
                logger.info(f"OCR: Full response: {result}")
                return ""
            
            text = parsed_results[0].get("ParsedText", "")
            logger.info(f"OCR: Successfully extracted {len(text)} chars from photo")
            return text.strip()
    
    except asyncio.TimeoutError:
        logger.error("OCR: Request timeout (60s exceeded)")
        return ""
    except Exception as e:
        logger.error(f"OCR: Exception during extraction: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"OCR: Traceback:\n{traceback.format_exc()}")
        return ""


# Legacy callbacks - not used in new design
@router.callback_query(F.data == "doc_clear")
async def cb_doc_clear(query: CallbackQuery, state: FSMContext) -> None:
    """Очистить документ (legacy)."""
    await state.clear()
    await state.set_state(ConversationStates.ready)
    await query.message.answer("🗑️ Документ очищен. Загружайте новый.")
    await query.answer()


@router.callback_query(F.data == "doc_info")
async def cb_doc_info(query: CallbackQuery, state: FSMContext) -> None:
    """Показать инфо doc (legacy)."""
    data = await state.get_data()
    document_name = data.get("document_name", "Unknown")
    document_size = data.get("document_size", 0)
    
    text = (
        f"📋 *Информация о документе*\n\n"
        f"*Имя:* `{document_name}`\n"
        f"*Размер:* {document_size:,} символов"
    )
    
    await query.message.answer(text, parse_mode="Markdown")
    await query.answer()
