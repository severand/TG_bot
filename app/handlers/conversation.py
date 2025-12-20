"""Conversation mode handlers for interactive document analysis.

Fixes 2025-12-20:
- Prompt selection keyboard: 2 buttons per row for better layout
- Photo upload: no 'photo ready' confirmation, only progress message
- Progress message auto-deleted after analysis results sent
- Logging order fixed: photo loaded log before analysis (not after)

Users now select prompt TYPE BEFORE uploading document.
Workflow: /analyze -> Select prompt -> Upload document -> Analyze
Full prompt selection integration.
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
    """Get keyboard with list of available prompts - 2 buttons per row."""
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
    builder.button(text="« Отмена", callback_data="analyze_cancel")
    builder.adjust(2)  # 2 buttons per row
    
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
        "📋 *Анализ документов*\n\n"
        "Шаг 1️⃣ из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов*\n\n"
        "🔙 *Как это работает:*\n"
        "1️⃣ Выберите промпт (тип анализа)\n"
        "2️⃣ Загрузите документ\n"
        "3️⃣ Получите результат\n\n"
        "👇 Ниже выберите тип анализа:"
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
        await query.answer("❌ Промпт не найден", show_alert=True)
        return
    
    # Save prompt to state
    await state.update_data(selected_prompt_name=prompt_name)
    
    # Move to document upload state
    await state.set_state(ConversationStates.ready)
    
    text = (
        f"✅ *Промпт выбран!*\n\n"
        f"📄 *Тип анализа:* `{prompt_name}`\n"
        f"_{prompt.description}_\n\n"
        f"📂 *Шаг 2️⃣ из 2:* Загрузите документ\n\n"
        f"📄 *Поддерживаемые форматы:*\n"
        f"• PDF\n• DOCX\n• TXT\n• ZIP\n• 📸 Фото документа\n\n"
        f"📁 Готово? Отправьте документ!"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="analyze_back_to_prompts")]]
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
        "📋 *Анализ документов*\n\n"
        "Шаг 1️⃣ из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов*\n\n"
        "👇 Ниже выберите тип анализа:"
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
    
    text = "❌ *Отменено*\n\nВозвращаемся в режим диалога."
    
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
        await message.answer("❌ Документ не найден")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    
    logger.info(f"User {message.from_user.id} uploading document: {document.file_name} ({file_size} bytes)")
    
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
            await message.answer("❌ Не удалось получить путь к файлу")
            await status_msg.delete()
            return
        
        # Generate unique filename
        file_ext = Path(document.file_name or "document").suffix or ".bin"
        temp_file_path = temp_user_dir / f"{uuid.uuid4()}{file_ext}"
        
        await bot.download_file(file.file_path, temp_file_path)
        logger.info(f"Downloaded: {temp_file_path} ({file_size} bytes)")
        
        # Extract text
        await status_msg.edit_text(
            "🔍 Обрабатываю документ...\n"
            "Извлечение текста..."
        )
        
        converter = FileConverter()
        extracted_text = converter.extract_text(temp_file_path, temp_user_dir)
        
        if not extracted_text or not extracted_text.strip():
            await message.answer(
                "⚠️ В документе не найден текст.\n"
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
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        # Log BEFORE analysis starts
        logger.info(
            f"Document loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars with prompt '{selected_prompt_name}'"
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
        await message.answer(f"❌ Ошибка: {str(e)}")
        await status_msg.delete()
    
    finally:
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.message(ConversationStates.ready, F.photo)
async def handle_photo_upload(message: Message, state: FSMContext) -> None:
    """Handle photo upload with OCR extraction - progress only, no confirmation."""
    if not message.photo:
        await message.answer("❌ Фото не найдено")
        return
    
    logger.info(f"User {message.from_user.id} uploading photo")
    
    # Show processing ONLY - no confirmation message after
    status_msg = await message.answer(
        "⏳ Обрабатываю фото...\n"
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
        
        # Move to ready for analysis state
        await state.set_state(ConversationStates.waiting_for_command)
        
        # Get prompt info from state
        data = await state.get_data()
        selected_prompt_name = data.get("selected_prompt_name", "default")
        
        # Log BEFORE analysis starts - FIXED ORDER
        logger.info(
            f"Photo loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars with prompt '{selected_prompt_name}'"
        )
        
        # Update status message with analysis start - NO "photo ready" message
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
        if temp_user_dir and temp_user_dir.exists():
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
    
    # Create progress message
    status_msg = await message.answer(
        "⏳ Анализирую по вашей инструкции...\n"
        "Это может занять некоторое время..."
    )
    
    await _perform_analysis(message, state, data, status_msg, additional_instruction=command)


async def _perform_analysis(
    message: Message, 
    state: FSMContext, 
    data: dict,
    status_msg: Message = None,
    additional_instruction: str = None,
) -> None:
    """Perform analysis with selected prompt. Auto-delete progress message after sending results."""
    document_text = data.get("document_text")
    document_name = data.get("document_name")
    selected_prompt_name = data.get("selected_prompt_name", "default")
    
    if not document_text:
        await message.answer("⚠️ Документ не загружен.")
        if status_msg:
            await status_msg.delete()
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
                "❌ Промпт не найден. Используется стандартный..."
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
            await message.answer("❌ Анализ не удался. Попробуйте ещё раз.")
            if status_msg:
                await status_msg.delete()
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
        
        # Delete progress message after results sent
        if status_msg:
            await status_msg.delete()
        
        logger.info(
            f"Analysis completed for user {message.from_user.id}: "
            f"{len(analysis_result)} chars in {len(chunks)} parts"
        )
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
        if status_msg:
            await status_msg.delete()


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
    await query.message.answer("🗑️ Документ очищен. Загрузите новый.")
    await query.answer()


@router.callback_query(F.data == "doc_info")
async def cb_doc_info(query: CallbackQuery, state: FSMContext) -> None:
    """Show doc info (legacy)."""
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
