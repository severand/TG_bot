"""RAG Knowledge Base handlers with persistent storage and LLM integration.

Updated: 2025-12-25
- Uses RAGManager with ChromaDB (persistent storage)
- Async embeddings (non-blocking)
- LLM integration for intelligent analysis
- Rich metadata tracking
- Batch processing for large documents

Architecture:
- RAGManager: orchestrates all RAG operations
- ChromaDB: persistent vector storage
- LLMFactory: intelligent analysis of search results
- MenuManager: unified UI
"""

import logging
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, Document, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import get_settings
from app.states.rag import RAGStates
from app.utils.menu import MenuManager, create_keyboard
from app.utils.cleanup import CleanupManager
from app.services.llm.llm_factory import LLMFactory

# Import RAG Manager
try:
    from rag_knowledge_base.rag_module.services.manager import RAGManager
    from rag_knowledge_base.rag_module.config import get_config as get_rag_config
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGManager = None  # type: ignore

logger = logging.getLogger(__name__)
router = Router()
config = get_settings()

# Initialize LLM Factory for AI analysis
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)

# Initialize RAG Manager (persistent storage with ChromaDB)
rag_manager: Optional['RAGManager'] = None


def get_rag_manager() -> 'RAGManager':
    """Get or initialize RAG Manager.
    
    Returns:
        RAGManager instance with persistent storage
        
    Raises:
        RuntimeError: If RAG module is not available
    """
    global rag_manager
    if not RAG_AVAILABLE:
        raise RuntimeError("RAG module not available")
    
    if rag_manager is None:
        try:
            rag_manager = RAGManager()  # type: ignore
            logger.info("RAG Manager initialized with persistent storage")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Manager: {e}")
            raise
    
    return rag_manager


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(Command("rag"))
async def cmd_rag(message: Message, state: FSMContext) -> None:
    """Activate RAG knowledge base mode."""
    if not RAG_AVAILABLE:
        await message.answer(
            "❌ RAG модуль недоступен\n\n"
            "Установите зависимости:\n"
            "`pip install -r rag_knowledge_base/requirements.txt`",
            parse_mode="Markdown",
        )
        return
    
    try:
        get_rag_manager()
        logger.info(f"User {message.from_user.id} activated /rag")
        await show_rag_main_menu(message=message, state=state)
    except Exception as e:
        logger.error(f"Error activating RAG: {e}")
        await message.answer(
            f"❌ Ошибка инициализации RAG модуля:\n\n{str(e)[:100]}",
            parse_mode="Markdown",
        )


# ============================================================================
# MAIN MENU
# ============================================================================

async def show_rag_main_menu(
    callback: CallbackQuery = None,
    message: Message = None,
    state: FSMContext = None,
) -> None:
    """Show RAG main menu with statistics."""
    user_id = message.from_user.id if message else callback.from_user.id
    
    try:
        manager = get_rag_manager()
        stats = manager.get_stats()
        
        doc_count = stats["total_documents"]
        chunk_count = stats["total_chunks"]
        
        text = (
            "🧠 *RAG Knowledge Base*\n\n"
            "Умная система поиска по документам с интеграцией AI.\n\n"
            f"📊 *Статус:*\n"
            f"• Документов: {doc_count}\n"
            f"• Фрагментов: {chunk_count}\n"
            f"• Модель: GPT-4o-mini\n\n"
            "📤 *Загрузка документов:*\n"
            "Поддерживает: PDF, DOCX, TXT, Excel, ZIP\n\n"
            "🔍 *Поиск:*\n"
            "Семантический поиск с анализом AI\n\n"
            "👇 Выберите действие:"
        )
        
        keyboard = create_keyboard([
            ("📤 Загрузить", "rag_upload"),
            ("🔍 Поиск + AI", "rag_search"),
            ("📊 Статистика", "rag_stats"),
            ("🗑️ Очистить", "rag_clear"),
            ("« Назад", "rag_cancel"),
        ], rows_per_row=2)
        
        await state.set_state(RAGStates.main_menu)
        
        await MenuManager.show_menu(
            callback=callback,
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_main_menu",
        )
    except Exception as e:
        logger.error(f"Error showing RAG menu: {e}")
        await message.answer(
            f"❌ Ошибка: {str(e)[:100]}",
            parse_mode="Markdown",
        )


# ============================================================================
# UPLOAD DOCUMENT
# ============================================================================

@router.callback_query(F.data == "rag_upload")
async def cb_rag_upload(query: CallbackQuery, state: FSMContext) -> None:
    """Start document upload flow."""
    text = (
        "📤 *Загрузка документа*\n\n"
        "Отправьте документ для добавления в базу знаний.\n\n"
        "📄 *Поддерживаемые форматы:*\n"
        "• PDF\n"
        "• DOCX, DOC\n"
        "• TXT\n"
        "• Excel (.xlsx, .xls)\n"
        "• ZIP архивы\n\n"
        "⚡ Документ будет автоматически обработан и проиндексирован.\n\n"
        "📁 Отправьте файл:"
    )
    
    keyboard = create_keyboard([
        ("« Назад", "rag_back_to_menu"),
    ], rows_per_row=1)
    
    await state.set_state(RAGStates.uploading)
    
    await MenuManager.navigate(
        callback=query,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=RAGStates.uploading,
        screen_code="rag_upload",
        preserve_data=True,
    )


@router.message(RAGStates.uploading, F.document)
async def handle_rag_document_upload(message: Message, state: FSMContext) -> None:
    """Handle document upload with persistent storage and async processing."""
    if not message.document:
        await message.answer("❌ Документ не найден")
        return
    
    document: Document = message.document
    file_size = document.file_size or 0
    user_id = message.from_user.id
    
    logger.info(f"RAG: User {user_id} uploading {document.file_name} ({file_size} bytes)")
    
    # Validate file size
    if file_size > config.MAX_FILE_SIZE:
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        await message.answer(
            f"⚠️ Файл слишком большой: {file_size / (1024 * 1024):.1f} MB\n"
            f"Максимум: {max_size_mb:.1f} MB"
        )
        return
    
    # Get menu_message_id
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    
    # Delete user message
    try:
        await message.delete()
    except:
        pass
    
    file_uuid = str(uuid.uuid4())
    temp_user_dir = None
    doc_id = f"user_{user_id}_doc_{file_uuid}"
    
    try:
        # Update status: downloading
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text="📥 Скачиваю файл...",
                    parse_mode="Markdown",
                )
            except:
                pass
        
        # Create temp directory
        temp_base = Path(config.TEMP_DIR)
        temp_base.mkdir(exist_ok=True)
        unique_temp_name = f"{user_id}_{file_uuid}"
        temp_user_dir = CleanupManager.create_temp_directory(temp_base, unique_temp_name)
        
        # Download file
        file = await message.bot.get_file(document.file_id)
        if not file.file_path:
            raise ValueError("Cannot get file path")
        
        file_ext = Path(document.file_name or "document").suffix or ".bin"
        temp_file_path = temp_user_dir / f"{file_uuid}{file_ext}"
        await message.bot.download_file(file.file_path, temp_file_path)
        
        # Update status: processing
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text="⚙️ Обрабатываю документ...\n✂️ Разбиваю на фрагменты...\n🧠 Генерирую embeddings...",
                    parse_mode="Markdown",
                )
            except:
                pass
        
        # Process document with RAG Manager (async)
        manager = get_rag_manager()
        
        # Run in thread pool to not block event loop
        document_obj = await asyncio.to_thread(
            manager.add_document,
            temp_file_path,
            doc_id,
            {
                "user_id": user_id,
                "original_filename": document.file_name,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file_size,
            }
        )
        
        logger.info(
            f"RAG: User {user_id} uploaded {document.file_name} "
            f"({document_obj.chunk_count} chunks, persisted to ChromaDB)"
        )
        
        # Get updated stats
        stats = manager.get_stats()
        doc_count = stats["total_documents"]
        chunk_count = stats["total_chunks"]
        
        text = (
            f"✅ *Документ загружен и сохранен!*\n\n"
            f"📄 Файл: `{document.file_name}`\n"
            f"📊 Фрагментов: {document_obj.chunk_count}\n"
            f"💾 Статус: Сохранено в базе (ChromaDB)\n\n"
            f"📈 *Всего в базе:*\n"
            f"• Документов: {doc_count}\n"
            f"• Фрагментов: {chunk_count}\n\n"
            f"✨ Теперь можете искать по всем документам!\n\n"
            f"👇 Выберите действие:"
        )
        
        keyboard = create_keyboard([
            ("📤 Загрузить ещё", "rag_upload"),
            ("🔍 Поиск", "rag_search"),
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=2)
        
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_upload_success",
        )
    
    except Exception as e:
        logger.error(f"RAG upload error: {e}")
        
        text = (
            f"❌ *Ошибка загрузки*\n\n"
            f"```\n{str(e)[:150]}\n```\n\n"
            f"Попробуйте другой файл или обратитесь в поддержку."
        )
        
        keyboard = create_keyboard([
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=1)
        
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_upload_error",
        )
    
    finally:
        # Cleanup temp files
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


# ============================================================================
# SEARCH WITH LLM ANALYSIS
# ============================================================================

@router.callback_query(F.data == "rag_search")
async def cb_rag_search(query: CallbackQuery, state: FSMContext) -> None:
    """Start search flow."""
    user_id = query.from_user.id
    
    try:
        manager = get_rag_manager()
        stats = manager.get_stats()
        
        # Check if documents exist
        if stats["total_documents"] == 0:
            text = (
                "📚 *База знаний пуста*\n\n"
                "Сначала загрузите документы через 'Загрузить'.\n\n"
                "👇 Выберите действие:"
            )
            
            keyboard = create_keyboard([
                ("📤 Загрузить", "rag_upload"),
                ("« Назад", "rag_back_to_menu"),
            ], rows_per_row=2)
            
            await MenuManager.navigate(
                callback=query,
                state=state,
                text=text,
                keyboard=keyboard,
                new_state=RAGStates.main_menu,
                screen_code="rag_search_empty",
                preserve_data=True,
            )
            return
        
        text = (
            "🔍 *Поиск с AI анализом*\n\n"
            "Задайте вопрос на естественном языке.\n"
            "AI найдет релевантные документы и даст подробный ответ.\n\n"
            "*Примеры:*\n"
            "• Какие условия оплаты?\n"
            "• На какую сумму застрахована?\n"
            "• Сроки поставки товара?\n\n"
            "💬 Напишите ваш вопрос:"
        )
        
        keyboard = create_keyboard([
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=1)
        
        await state.set_state(RAGStates.searching)
        
        await MenuManager.navigate(
            callback=query,
            state=state,
            text=text,
            keyboard=keyboard,
            new_state=RAGStates.searching,
            screen_code="rag_search",
            preserve_data=True,
        )
    except Exception as e:
        logger.error(f"Error starting search: {e}")
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)[:100]}",
            parse_mode="Markdown",
        )


@router.message(RAGStates.searching, F.text)
async def handle_rag_search_query(message: Message, state: FSMContext) -> None:
    """Handle search query with semantic search + LLM analysis."""
    user_id = message.from_user.id
    query_text = message.text
    
    if not query_text or not query_text.strip():
        return
    
    logger.info(f"RAG: User {user_id} searching '{query_text}'")
    
    # Get menu_message_id
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    
    # Delete user message
    try:
        await message.delete()
    except:
        pass
    
    # Update menu with processing status
    if menu_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_message_id,
                text=f"🔍 Ищу в документах: `{query_text[:40]}...`",
                parse_mode="Markdown",
            )
        except:
            pass
    
    try:
        manager = get_rag_manager()
        
        # Semantic search (async)
        search_results = await asyncio.to_thread(
            manager.search,
            query_text,
            top_k=5
        )
        
        # Filter by relevance
        relevant_results = [r for r in search_results if r.similarity_score >= 0.3]
        
        if not relevant_results:
            text = (
                f"🤔 *Не найдено релевантной информации*\n\n"
                f"По запросу `{query_text}` не найдено подходящих документов.\n\n"
                f"Попробуйте:\n"
                f"• Переформулировать вопрос\n"
                f"• Загрузить больше документов\n"
                f"• Использовать более общие термины\n\n"
                f"👇 Выберите действие:"
            )
            
            keyboard = create_keyboard([
                ("🔍 Новый поиск", "rag_search"),
                ("« Назад", "rag_back_to_menu"),
            ], rows_per_row=2)
            
            await MenuManager.show_menu(
                message=message,
                state=state,
                text=text,
                keyboard=keyboard,
                screen_code="rag_search_not_found",
            )
            return
        
        # Update status: analyzing with AI
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text=f"🤖 Анализирую найденные документы с AI...",
                    parse_mode="Markdown",
                )
            except:
                pass
        
        # Prepare context for LLM
        context_parts = []
        for i, result in enumerate(relevant_results[:3], 1):
            chunk = result.chunk
            relevance_pct = int(result.similarity_score * 100)
            source = chunk.metadata.get("source_file", "unknown")
            page = chunk.metadata.get("page")
            
            page_info = f" (стр. {page})" if page else ""
            context_parts.append(
                f"[Документ {i}{page_info}, {relevance_pct}% релевантности]\n"
                f"Источник: {source}\n"
                f"Текст: {chunk.text[:300]}...\n"
            )
        
        context = "\n".join(context_parts)
        
        # Create prompt for LLM
        llm_system_prompt = (
            "Ты помощник, анализирующий документы. "
            "Отвечай конкретно на основе представленного контекста. "
            "Ссылайся на документы. Максимум 200 слов."
        )
        
        llm_user_prompt = (
            f"На основе следующих фрагментов документов ответь на вопрос пользователя.\n\n"
            f"КОНТЕКСТ ИЗ ДОКУМЕНТОВ:\n{context}\n\n"
            f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {query_text}\n\n"
            f"ОТВЕТ:"
        )
        
        # Call LLM for analysis
        logger.info(f"RAG: Calling LLM for analysis (query: {query_text[:50]}) for user {user_id}")
        
        llm_response = await llm_factory.analyze_document(
            context,
            llm_user_prompt,
            system_prompt=llm_system_prompt,
            use_streaming=False,
            user_id=user_id,
        )
        
        if not llm_response:
            llm_response = "❌ Не удалось получить ответ от AI"
        
        # Build response
        text = f"🎯 *Результаты поиска для:* `{query_text}`\n\n"
        text += f"💡 *AI Анализ:*\n{llm_response}\n\n"
        text += "*📄 Найденные документы:*\n"
        
        for i, result in enumerate(relevant_results[:3], 1):
            chunk = result.chunk
            relevance_pct = int(result.similarity_score * 100)
            source = chunk.metadata.get("source_file", "unknown")
            page = chunk.metadata.get("page")
            
            page_info = f" (стр. {page})" if page else ""
            emoji = "🎯" if relevance_pct > 80 else "📌" if relevance_pct > 60 else "📄"
            
            text += (
                f"\n{emoji} *Док. {i}* ({relevance_pct}%){page_info}\n"
                f"📄 `{source}`\n"
                f"__{chunk.text[:150]}...__\n"
            )
        
        text += "\n👇 Выберите действие:"
        
        keyboard = create_keyboard([
            ("🔍 Новый поиск", "rag_search"),
            ("📤 Загрузить документ", "rag_upload"),
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=2)
        
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_search_results",
        )
        
        logger.info(f"RAG: User {user_id} search complete - found {len(relevant_results)} results")
    
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        
        text = (
            f"❌ *Ошибка поиска*\n\n"
            f"```\n{str(e)[:150]}\n```\n\n"
            f"Попробуйте ещё раз или обратитесь в поддержку."
        )
        
        keyboard = create_keyboard([
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=1)
        
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_search_error",
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.callback_query(F.data == "rag_stats")
async def cb_rag_stats(query: CallbackQuery, state: FSMContext) -> None:
    """Show RAG statistics."""
    try:
        manager = get_rag_manager()
        stats = manager.get_stats()
        
        text = (
            f"📊 *Статистика RAG базы знаний*\n\n"
            f"📚 Документов: {stats['total_documents']}\n"
            f"📄 Фрагментов: {stats['total_chunks']}\n"
            f"🧠 Embedding модель: paraphrase-multilingual-MiniLM-L12-v2\n"
            f"📐 Размер вектора: {stats['embedding_dimension']}D\n"
            f"🎯 Порог релевантности: {int(stats['similarity_threshold'] * 100)}%\n\n"
        )
        
        if stats["total_documents"] > 0:
            text += "*Загруженные документы:*\n"
            for doc in stats["documents"]:
                size_kb = doc["size"] / 1024
                text += f"  • `{doc['filename']}`: {doc['chunks']} чанков ({size_kb:.1f} KB)\n"
        else:
            text += "📭 База знаний пуста\n"
        
        text += "\n👇 Выберите действие:"
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        text = f"❌ Ошибка: {str(e)[:100]}"
    
    keyboard = create_keyboard([
        ("« Назад", "rag_back_to_menu"),
    ], rows_per_row=1)
    
    await MenuManager.navigate(
        callback=query,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=RAGStates.main_menu,
        screen_code="rag_stats",
        preserve_data=True,
    )


# ============================================================================
# CLEAR DATABASE
# ============================================================================

@router.callback_query(F.data == "rag_clear")
async def cb_rag_clear(query: CallbackQuery, state: FSMContext) -> None:
    """Clear RAG storage (confirmation)."""
    text = (
        "🗑️ *Очистить базу знаний?*\n\n"
        "⚠️ Это действие удалит ВСЕ документы и фрагменты!\n\n"
        "Подтвердите удаление:"
    )
    
    keyboard = create_keyboard([
        ("✅ Да, удалить всё", "rag_confirm_clear"),
        ("❌ Отмена", "rag_back_to_menu"),
    ], rows_per_row=2)
    
    await MenuManager.navigate(
        callback=query,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=RAGStates.main_menu,
        screen_code="rag_clear_confirm",
        preserve_data=True,
    )


@router.callback_query(F.data == "rag_confirm_clear")
async def cb_rag_confirm_clear(query: CallbackQuery, state: FSMContext) -> None:
    """Confirm clear RAG storage."""
    try:
        manager = get_rag_manager()
        manager.clear_all()
        
        text = (
            "🗑️ *База знаний очищена*\n\n"
            "✅ Все документы удалены\n"
            "✅ Все embeddings удалены\n"
            "✅ ChromaDB очищена\n\n"
            "👇 Выберите действие:"
        )
        logger.info(f"User {query.from_user.id} cleared RAG database")
    
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        text = f"❌ Ошибка при очистке: {str(e)[:100]}\n\n👇 Выберите действие:"
    
    keyboard = create_keyboard([
        ("« Назад", "rag_back_to_menu"),
    ], rows_per_row=1)
    
    await MenuManager.navigate(
        callback=query,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=RAGStates.main_menu,
        screen_code="rag_clear_done",
        preserve_data=True,
    )


# ============================================================================
# NAVIGATION
# ============================================================================

@router.callback_query(F.data == "rag_back_to_menu")
async def cb_rag_back_to_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Return to RAG main menu."""
    await show_rag_main_menu(callback=query, state=state)


@router.callback_query(F.data == "rag_cancel")
async def cb_rag_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Cancel RAG mode."""
    await state.clear()
    
    text = "❌ *RAG режим отменен*\n\nВозвращаемся в диалог."
    
    await query.message.edit_text(text, parse_mode="Markdown")
    await query.answer()
    logger.info(f"User {query.from_user.id} exited RAG mode")
