"""Conversation mode handlers for interactive document analysis.

Fixes 2025-12-20:
- Users now select prompt TYPE BEFORE uploading document
- Workflow: /analyze -> Select prompt -> Upload document -> Analyze
- Full prompt selection integration

Simplified: Just upload documents and send analysis instructions.
No menus, no buttons - clean workflow via /analyze command.
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
    """Get keyboard with list of available prompts."""
    prompts = prompt_manager.list_prompts(user_id)
    
    builder = InlineKeyboardBuilder()
    
    # Add all prompts
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        button_text = f"{prompt.description[:40]}"
        builder.button(
            text=button_text,
            callback_data=f"analyze_select_prompt_{name}"
        )
    
    # Back button
    builder.button(text="\u00ab \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="analyze_cancel")
    builder.adjust(1)  # One button per row for readability
    
    return builder.as_markup()


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    """Activate document analysis mode - now with prompt selection."""
    logger.info(f"User {message.from_user.id} activated /analyze")
    await start_analyze_mode(message=message, state=state)


async def start_analyze_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Start interactive document analysis mode.
    
    NEW: Show prompt selection FIRST, then ask for document.
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
    prompts = prompt_manager.list_prompts(user_id)
    
    await state.set_state(ConversationStates.selecting_prompt)
    
    text = (
        "\ud83d\udcca *\u0410\u043d\u0430\u043b\u0438\u0437 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432*\n\n"
        "\u0428\u0430\u0433 1\ufe0f\u20e3 \u0438\u0437 2: *\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430*\n\n"
        f"\ud83d\udcc4 *\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e: {len(prompts)} \u043f\u0440\u043e\u043c\u043f\u0442\u043e\u0432*\n\n"
        "\ud83d\udd19 *\u041a\u0430\u043a \u044d\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442:*\n"
        "1\ufe0f\u20e3 \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u043c\u043f\u0442 (\u0442\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430)\n"
        "2\ufe0f\u20e3 \u0417\u0430\u0433\u0440\u0443\u0436\u0442\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\n"
        "3\ufe0f\u20e3 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u0435 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\n\n"
        "\ud83d\udc47 \u041d\u0438\u0436\u0435 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430:"
    )
    
    if message:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        logger.info(f"Analysis mode started for user {user_id}")
    elif callback:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        await callback.answer()
        logger.info(f"Analysis mode started for user {user_id}")


@router.callback_query(F.data.startswith("analyze_select_prompt_"))
async def cb_select_prompt(query: CallbackQuery, state: FSMContext) -> None:
    """Handle prompt selection - move to document upload state."""
    prompt_name = query.data.replace("analyze_select_prompt_", "")
    user_id = query.from_user.id
    
    # Verify prompt exists
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    if not prompt:
        await query.answer("\u274c \u041f\u0440\u043e\u043c\u043f\u0442 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d", show_alert=True)
        return
    
    # Save prompt to state
    await state.update_data(selected_prompt_name=prompt_name)
    
    # Move to document upload state
    await state.set_state(ConversationStates.ready)
    
    text = (
        f"\u2705 *\u041f\u0440\u043e\u043c\u043f\u0442 \u0432\u044b\u0431\u0440\u0430\u043d!*\n\n"
        f"\ud83d\udcc4 *\u0422\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430:* `{prompt_name}`\n"
        f"_{prompt.description}_\n\n"
        f"\ud83d\udcc2 *\u0428\u0430\u0433 2\ufe0f\u20e3 \u0438\u0437 2:* \u0417\u0430\u0433\u0440\u0443\u0436\u0442\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\n\n"
        f"\ud83d\udcc4 *\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u043c\u044b\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u044b:*\n"
        f"\u2022 PDF\n\u2022 DOCX\n\u2022 TXT\n\u2022 ZIP\n\u2022 \ud83d\udcc3 \u0424\u043e\u0442\u043e \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\n\n"
        f"\ud83d\udcc1 \u0413\u043e\u0442\u043e\u0432? \u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442!"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="\u00ab \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="analyze_back_to_prompts")]]
        ),
    )
    
    logger.info(f"User {user_id} selected prompt: {prompt_name}")
    await query.answer()


@router.callback_query(F.data == "analyze_back_to_prompts")
async def cb_back_to_prompts(query: CallbackQuery, state: FSMContext) -> None:
    """Go back to prompt selection."""
    user_id = query.from_user.id
    prompts = prompt_manager.list_prompts(user_id)
    
    text = (
        "\ud83d\udcca *\u0410\u043d\u0430\u043b\u0438\u0437 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u0432*\n\n"
        "\u0428\u0430\u0433 1\ufe0f\u20e3 \u0438\u0437 2: *\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430*\n\n"
        f"\ud83d\udcc4 *\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e: {len(prompts)} \u043f\u0440\u043e\u043c\u043f\u0442\u043e\u0432*\n\n"
        "\ud83d\udc47 \u041d\u0438\u0436\u0435 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u0430\u043d\u0430\u043b\u0438\u0437\u0430:"
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
    """Cancel analyze mode."""
    await state.clear()
    
    text = "\u274c *\u041e\u0442\u043c\u0435\u043d\u043d\u043e*\n\nVозвращаемся в режим диалога."
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} cancelled analyze mode")


@router.message(ConversationStates.ready, F.document)
async def handle_document_upload(message: Message, state: FSMContext) -> None:
    """Handle document upload - extract and save."""
    if not message.document:
        await message.answer("\u274c Документ не найден")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    
    logger.info(f"User {message.from_user.id} uploading document: {document.file_name} ({file_size} bytes)")
    
    # Validate file size
    if file_size > config.MAX_FILE_SIZE:
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"\u26a0\ufe0f Файл слишком большой: {file_size / (1024 * 1024):.1f} MB\n"
            f"Максимум: {max_size_mb:.1f} MB"
        )
        return
    
    # Show processing
    status_msg = await message.answer(
        "\ud83d\udd0d Обрабатываю документ...\n"
        "Скачивание и извлечение текста..."
    )
    
    temp_user_dir = None
    
    try:
        # Create temp directory
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            message.from_user.id,
        )
        
        # Download file
        bot = message.bot
        file: File = await bot.get_file(document.file_id)
        
        if not file.file_path:
            await message.answer("\u274c Не удалось получить путь к файлу")
            await status_msg.delete()
            return
        
        # Generate unique filename
        file_ext = Path(document.file_name or "document").suffix or ".bin"
        temp_file_path = temp_user_dir / f"{uuid.uuid4()}{file_ext}"
        
        await bot.download_file(file.file_path, temp_file_path)
        logger.info(f"Downloaded: {temp_file_path} ({file_size} bytes)")
        
        # Extract text
        await status_msg.edit_text(
            "\ud83d\udd0d Обрабатываю документ...\n"
            "Извлечение текста..."
        )
        
        converter = FileConverter()
        extracted_text = converter.extract_text(temp_file_path, temp_user_dir)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "\u26a0\ufe0f В документе не найден текст.\n"
                "Попробуйте другой файл."
            )
            await status_msg.delete()
            return
        
        # Save to state
        await state.update_data(
            document_text=extracted_text,
            document_name=document.file_name or "document",
            document_size=len(extracted_text),
            user_id=message.from_user.id,
        )
        
        # Move to ready for analysis state
        await state.set_state(ConversationStates.waiting_for_command)
        
        # Confirm
        await status_msg.delete()
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        text = (
            f"\u2705 *Документ готов!*\n\n"
            f"*Файл:* `{document.file_name or 'document'}`\n"
            f"*Размер:* {len(extracted_text):,} символов\n"
            f"*Тип анализа:* `{selected_prompt_name}`\n\n"
            f"\ud83d\udcc1 Начинаю анализ...\n\n"
            f"\ud83d\udd24 Или напишите дополнительную инструкцию, если нужно уточнить анализ."
        )
        
        await message.answer(
            text,
            parse_mode="Markdown",
        )
        
        # Immediately start analysis with selected prompt
        await _perform_analysis(message, state, data)
        
        logger.info(
            f"Document loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars with prompt '{selected_prompt_name}'"
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer(f"\u274c Ошибка: {str(e)}")
        await status_msg.delete()
    
    finally:
        if temp_user_dir and not temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(ConversationStates.ready, F.photo)
async def handle_photo_upload(message: Message, state: FSMContext) -> None:
    """Handle photo upload with OCR extraction (same as documents handler)."""
    if not message.photo:
        await message.answer("\u274c Фото не найдено")
        return
    
    logger.info(f"User {message.from_user.id} uploading photo")
    
    # Show processing
    status_msg = await message.answer(
        "\ud83d\udcc3 Обрабатываю фото...\n"
        "Распознавание текста (OCR)..."
    )
    
    temp_user_dir = None
    
    try:
        # Create temp directory
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        temp_user_dir = CleanupManager.create_temp_directory(
            temp_base,
            message.from_user.id,
        )
        
        # Extract text from photo using OCR
        extracted_text = await _extract_text_from_photo_for_analysis(message, temp_user_dir)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "\u26a0\ufe0f Текст в фото не найден.\n"
                "Убедитесь что:" 
                "\n\u2022 Фото четкое\n\u2022 Текст хорошо виден\n\u2022 Контрастный фон"
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
        
        # Move to ready for analysis state
        await state.set_state(ConversationStates.waiting_for_command)
        
        # Confirm
        await status_msg.delete()
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        text = (
            f"\u2705 *Фото готово!*\n\n"
            f"*Размер:* {len(extracted_text):,} символов\n"
            f"*Тип анализа:* `{selected_prompt_name}`\n\n"
            f"\ud83d\udd24 Начинаю анализ...\n\n"
            f"Или напишите дополнительную инструкцию для уточнения."
        )
        
        await message.answer(
            text,
            parse_mode="Markdown",
        )
        
        # Immediately start analysis with selected prompt
        await _perform_analysis(message, state, data)
        
        logger.info(
            f"Photo loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars with prompt '{selected_prompt_name}'"
        )
    
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer(f"\u274c Ошибка: {str(e)}")
        await status_msg.delete()
    
    finally:
        if temp_user_dir and not temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(ConversationStates.waiting_for_command, F.text)
async def handle_analysis_command(message: Message, state: FSMContext) -> None:
    """Handle optional additional instruction for analysis."""
    command = message.text.strip()
    
    if not command:
        await message.answer("Укажите инструкцию для анализа.")
        return
    
    # Check for special commands
    if command.startswith("/"):
        return
    
    data = await state.get_data()
    
    # Use additional instruction if provided
    await state.update_data(additional_instruction=command)
    await _perform_analysis(message, state, data, additional_instruction=command)


async def _perform_analysis(
    message: Message, 
    state: FSMContext, 
    data: dict,
    additional_instruction: str = None,
) -> None:
    """Perform analysis with selected prompt."""
    document_text = data.get("document_text")
    document_name = data.get("document_name")
    selected_prompt_name = data.get("selected_prompt_name", "default")
    
    if not document_text:
        await message.answer("\u26a0\ufe0f Документ не загружен.")
        return
    
    logger.info(
        f"User {message.from_user.id} starting analysis with prompt '{selected_prompt_name}'"
    )
    
    # Show typing
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Get selected prompt
        prompt = prompt_manager.get_prompt(message.from_user.id, selected_prompt_name)
        
        if not prompt:
            prompt = prompt_manager.get_prompt(message.from_user.id, "default")
        
        if not prompt:
            await message.answer(
                "\u274c Промпт не найден. Используется стандартный..."
            )
        
        # Build analysis command
        if additional_instruction:
            analysis_command = additional_instruction
        else:
            analysis_command = prompt.user_prompt_template if prompt else "Проанализируй этот документ и предоставь ключевые выводы."
        
        # Analyze
        analysis_result = await llm_factory.analyze_document(
            document_text,
            analysis_command,
            system_prompt=prompt.system_prompt if prompt else None,
            use_streaming=False,
        )
        
        if not analysis_result:
            await message.answer("\u274c Анализ не удался. Попробуйте ещё раз.")
            return
        
        # Split and send
        splitter = TextSplitter(max_length=4000)
        chunks = splitter.split(analysis_result)
        
        if len(chunks) == 1:
            await message.answer(
                analysis_result,
                parse_mode="Markdown",
            )
        else:
            for i, chunk in enumerate(chunks, 1):
                prefix = f"*[Часть {i}/{len(chunks)}]*\n\n"
                await message.answer(
                    f"{prefix}{chunk}",
                    parse_mode="Markdown",
                )
        
        logger.info(
            f"Analysis completed for user {message.from_user.id}: "
            f"{len(analysis_result)} chars in {len(chunks)} parts"
        )
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await message.answer(f"\u274c Ошибка: {str(e)[:100]}")


async def _extract_text_from_photo_for_analysis(
    message: Message,
    temp_dir: Path,
) -> str:
    """Extract text from photo using OCR.space cloud API.
    
    Args:
        message: Message with photo
        temp_dir: Temporary directory
        
    Returns:
        Extracted text from photo
    """
    try:
        import httpx
        import base64
        
        # Get largest photo
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Download photo
        temp_file = temp_dir / f"photo_{photo.file_unique_id}.jpg"
        await message.bot.download_file(file_info.file_path, temp_file)
        
        # Read photo as base64
        with open(temp_file, "rb") as f:
            photo_bytes = f.read()
        
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        
        # Call OCR.space API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.ocr.space/parse/image",
                data={
                    "apikey": config.OCR_SPACE_API_KEY,
                    "base64Image": f"data:image/jpeg;base64,{photo_base64}",
                    "language": "rus",  # Russian
                    "isOverlayRequired": False,
                    "detectOrientation": True,
                    "scale": True,
                    "OCREngine": 2,  # Engine 2 for better accuracy
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                logger.error(f"OCR.space API error: {response.status_code} {response.text}")
                return ""
            
            result = response.json()
            
            if result.get("IsErroredOnProcessing"):
                error_msg = result.get("ErrorMessage", ["Unknown error"])
                logger.error(f"OCR processing error: {error_msg}")
                return ""
            
            # Extract text from all parsed results
            parsed_results = result.get("ParsedResults", [])
            if not parsed_results:
                logger.warning("No text detected in image")
                return ""
            
            text = parsed_results[0].get("ParsedText", "")
            logger.info(f"OCR: Extracted {len(text)} chars from photo")
            return text.strip()
    
    except Exception as e:
        logger.error(f"Failed to extract text from photo via OCR: {e}")
        return ""


# Legacy callbacks - not used in new design
@router.callback_query(F.data == "doc_clear")
async def cb_doc_clear(query: CallbackQuery, state: FSMContext) -> None:
    """Clear document (legacy)."""
    await state.clear()
    await state.set_state(ConversationStates.ready)
    await query.message.answer("\ud83d\uddd1\ufe0f Документ очищен. Загрузите новый.")
    await query.answer()


@router.callback_query(F.data == "doc_info")
async def cb_doc_info(query: CallbackQuery, state: FSMContext) -> None:
    """Show doc info (legacy)."""
    data = await state.get_data()
    document_name = data.get("document_name", "Unknown")
    document_size = data.get("document_size", 0)
    
    text = (
        f"\ud83d\udcc2 *Информация о документе*\n\n"
        f"*Имя:* `{document_name}`\n"
        f"*Размер:* {document_size:,} символов"
    )
    
    await query.message.answer(text, parse_mode="Markdown")
    await query.answer()
