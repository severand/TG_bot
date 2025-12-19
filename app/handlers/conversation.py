"""Conversation mode handlers for interactive document analysis.

Simplified: Just upload documents and send analysis instructions.
No menus, no buttons - clean workflow via /analyze command.
"""

import logging
import uuid
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, Document, File, CallbackQuery
from aiogram.fsm.context import FSMContext

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


@router.message(F.text == "/analyze")
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    """Activate document analysis mode."""
    await start_analyze_mode(message=message, state=state)


async def start_analyze_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Start interactive document analysis mode.
    
    Simple activation - just explain and wait for document.
    """
    if state is None:
        logger.error("state is None in start_analyze_mode")
        return
    
    await state.set_state(ConversationStates.ready)
    
    text = (
        "📊 *Режим анализа документов активен*\n\n"
        "📝 *Как это работает:*\n"
        "1️⃣ Загрузите документ (PDF, DOCX, TXT, ZIP)\n"
        "2️⃣ Бот подтвердит готовность\n"
        "3️⃣ Напишите инструкцию для анализа\n"
        "4️⃣ Получите результат\n\n"
        "📎 *Пример:*\n"
        "• Загрузите contract.pdf\n"
        "• Напишите: 'Найди все риски в этом договоре'\n"
        "• Получите детальный анализ\n\n"
        "📤 *Готов? Загрузите документ!*"
    )
    
    if message:
        await message.answer(
            text,
            parse_mode="Markdown",
        )
    elif callback:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
        )
        await callback.answer()
    
    logger.info(f"Analysis mode started")


@router.message(ConversationStates.ready, F.document)
async def handle_document_upload(message: Message, state: FSMContext) -> None:
    """Handle document upload - extract and save."""
    if not message.document:
        await message.answer("❌ Документ не найден")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    
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
        
        # Move to conversation state
        await state.set_state(ConversationStates.waiting_for_command)
        
        # Confirm
        await status_msg.delete()
        
        text = (
            f"✅ *Документ готов!*\n\n"
            f"*Файл:* `{document.file_name or 'document'}`\n"
            f"*Размер:* {len(extracted_text):,} символов\n\n"
            f"📝 *Теперь напишите инструкцию для анализа:*\n\n"
            f"Примеры:\n"
            f"• 'Сделай краткое резюме'\n"
            f"• 'Найди все риски'\n"
            f"• 'Извлеки ключевые пункты'\n"
            f"• 'Проанализируй юридические аспекты'\n\n"
            f"🔄 Чтобы очистить: /cancel"
        )
        
        await message.answer(
            text,
            parse_mode="Markdown",
        )
        
        logger.info(
            f"Document loaded for user {message.from_user.id}: "
            f"{len(extracted_text)} chars"
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")
        await status_msg.delete()


@router.message(ConversationStates.waiting_for_command, F.text)
async def handle_analysis_command(message: Message, state: FSMContext) -> None:
    """Handle text commands for document analysis."""
    command = message.text.strip()
    
    if not command:
        await message.answer("Укажите инструкцию для анализа.")
        return
    
    # Check for special commands
    if command.startswith("/"):
        return
    
    data = await state.get_data()
    document_text = data.get("document_text")
    document_name = data.get("document_name")
    
    if not document_text:
        await message.answer(
            "⚠️ Документ не загружен.\n"
            "Загрузите документ сначала."
        )
        await state.set_state(ConversationStates.ready)
        return
    
    # Show typing
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Get user's default prompt
        default_prompt_name = data.get("default_prompt", "default")
        prompt = prompt_manager.get_prompt(message.from_user.id, default_prompt_name)
        
        if not prompt:
            prompt = prompt_manager.get_prompt(message.from_user.id, "default")
        
        # Analyze
        analysis_result = await llm_factory.analyze_document(
            document_text,
            command,
            system_prompt=prompt.system_prompt if prompt else None,
            use_streaming=False,
        )
        
        if not analysis_result:
            await message.answer("❌ Анализ не удался. Попробуйте ещё раз.")
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
            f"instruction='{command[:30]}...'"
        )
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")


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
        f"📊 *Информация о документе*\n\n"
        f"*Имя:* `{document_name}`\n"
        f"*Размер:* {document_size:,} символов"
    )
    
    await query.message.answer(text, parse_mode="Markdown")
    await query.answer()
