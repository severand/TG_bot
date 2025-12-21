"""RAG Knowledge Base handlers.

Added: 2025-12-21 19:00

Provides intelligent document knowledge base with semantic search.
Users can upload documents and search through them using natural language.

Implementation:
- Uses SimpleRAG (without ChromaDB) for Windows compatibility
- In-memory storage (71% RAG functionality)
- MenuManager for unified menu (no multiple menus)
- 2 buttons per row keyboard
- Follows UNIFIED_MENU.md architecture
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document, CallbackQuery
from aiogram.fsm.context import FSMContext
import numpy as np

from app.config import get_settings
from app.states.rag import RAGStates
from app.utils.menu import MenuManager, create_keyboard
from app.utils.cleanup import CleanupManager
from app.utils.text_splitter import TextSplitter

# Import RAG components (works on Windows without ChromaDB)
try:
    from rag_knowledge_base.rag_module.file_processing import FileConverter as RAGConverter
    from rag_knowledge_base.rag_module.services import Chunker, EmbeddingService
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error("RAG module not available. Install requirements from rag_knowledge_base/")

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()

# Initialize RAG components if available
if RAG_AVAILABLE:
    rag_converter = RAGConverter()
    chunker = Chunker(chunk_size=500, chunk_overlap=50)
    embedder = EmbeddingService()

# In-memory document storage per user
# Structure: {user_id: [(text, embedding, metadata), ...]}
document_storage: Dict[int, List[Dict]] = {}


@router.message(Command("rag"))
async def cmd_rag(message: Message, state: FSMContext) -> None:
    """Activate RAG knowledge base mode.
    
    Shows main RAG menu with options to upload documents or search.
    """
    if not RAG_AVAILABLE:
        await message.answer(
            "❌ RAG модуль недоступен\n\n"
            "Установите зависимости:\n"
            "`pip install -r rag_knowledge_base/requirements.txt`",
            parse_mode="Markdown",
        )
        return
    
    logger.info(f"User {message.from_user.id} activated /rag")
    await show_rag_main_menu(message=message, state=state)


async def show_rag_main_menu(
    callback: CallbackQuery = None,
    message: Message = None,
    state: FSMContext = None,
) -> None:
    """Show RAG main menu.
    
    Options:
    - Upload document to knowledge base
    - Search in knowledge base
    - View statistics
    - Clear knowledge base
    """
    user_id = message.from_user.id if message else callback.from_user.id
    
    # Get statistics
    doc_count = 0
    chunk_count = 0
    if user_id in document_storage:
        chunks = document_storage[user_id]
        chunk_count = len(chunks)
        doc_count = len(set(c['filename'] for c in chunks))
    
    text = (
        "🧠 *RAG Knowledge Base*\n\n"
        "Умная база знаний с семантическим поиском.\n\n"
        f"📊 *Статус:*\n"
        f"• Документов: {doc_count}\n"
        f"• Фрагментов: {chunk_count}\n\n"
        "📤 *Загрузка документов:*\n"
        "Нажмите 'Загрузить', затем отправьте файл\n\n"
        "🔍 *Поиск:*\n"
        "Задавайте вопросы на естественном языке\n\n"
        "👇 Выберите действие:"
    )
    
    # Create keyboard - 2 buttons per row
    keyboard = create_keyboard([
        ("📤 Загрузить", "rag_upload"),
        ("🔍 Поиск", "rag_search"),
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
        "• ZIP\n\n"
        "⚡ Документ будет разбит на фрагменты и проиндексирован.\n\n"
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
    """Handle document upload to RAG knowledge base."""
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
    
    # Update menu with processing status
    if menu_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_message_id,
                text="🔄 Загружаю документ в базу знаний...\nИзвлечение текста...",
                parse_mode="Markdown",
            )
        except:
            pass
    
    file_uuid = str(uuid.uuid4())
    temp_user_dir = None
    
    try:
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
        
        # Extract text
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text="✂️ Разбиваю на фрагменты...",
                    parse_mode="Markdown",
                )
            except:
                pass
        
        text = rag_converter.extract_text(temp_file_path)
        
        if not text or not text.strip():
            raise ValueError("No text extracted from document")
        
        # Chunking
        chunks = chunker.chunk_text(text, document.file_name or "doc", {
            "filename": document.file_name,
            "user_id": user_id
        })
        
        # Generate embeddings
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=menu_message_id,
                    text=f"🧠 Генерирую embeddings ({len(chunks)} фрагментов)...",
                    parse_mode="Markdown",
                )
            except:
                pass
        
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_batch(texts)
        
        # Save to storage
        if user_id not in document_storage:
            document_storage[user_id] = []
        
        for chunk, embedding in zip(chunks, embeddings):
            document_storage[user_id].append({
                'text': chunk.text,
                'embedding': embedding,
                'filename': document.file_name,
                'position': chunk.position,
                'metadata': chunk.metadata
            })
        
        logger.info(f"RAG: User {user_id} uploaded {document.file_name} ({len(chunks)} chunks)")
        
        # Show success
        doc_count = len(set(c['filename'] for c in document_storage[user_id]))
        chunk_count = len(document_storage[user_id])
        
        text = (
            f"✅ *Документ загружен!*\n\n"
            f"📄 Файл: `{document.file_name}`\n"
            f"📊 Фрагментов: {len(chunks)}\n\n"
            f"💾 *Всего в базе:*\n"
            f"• Документов: {doc_count}\n"
            f"• Фрагментов: {chunk_count}\n\n"
            f"Теперь можете искать по документам!\n\n"
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
            f"{str(e)[:100]}\n\n"
            f"Попробуйте другой файл."
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
        # Cleanup
        if temp_user_dir and temp_user_dir.exists():
            await CleanupManager.cleanup_directory_async(temp_user_dir)


@router.callback_query(F.data == "rag_search")
async def cb_rag_search(query: CallbackQuery, state: FSMContext) -> None:
    """Start search flow."""
    user_id = query.from_user.id
    
    # Check if documents exist
    if user_id not in document_storage or not document_storage[user_id]:
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
        "🔍 *Поиск в базе знаний*\n\n"
        "Задайте вопрос на естественном языке.\n\n"
        "*Примеры:*\n"
        "• Условия оплаты\n"
        "• Сроки поставки\n"
        "• Гарантийные обязательства\n\n"
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


@router.message(RAGStates.searching, F.text)
async def handle_rag_search_query(message: Message, state: FSMContext) -> None:
    """Handle search query."""
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
                text=f"🔍 Ищу: `{query_text[:50]}...`",
                parse_mode="Markdown",
            )
        except:
            pass
    
    try:
        # Generate query embedding
        query_embedding = embedder.embed(query_text)
        
        # Calculate similarities
        similarities = []
        for chunk in document_storage[user_id]:
            # Cosine similarity
            similarity = float(np.dot(query_embedding, chunk['embedding']) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk['embedding'])
            ))
            similarities.append((chunk, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Top-3 results
        results = similarities[:3]
        
        # Build response
        if not any(score >= 0.3 for _, score in results):
            text = (
                f"🤔 *Не найдено*\n\n"
                f"По запросу `{query_text}` не найдено релевантной информации.\n\n"
                f"Попробуйте переформулировать вопрос.\n\n"
                f"👇 Выберите действие:"
            )
        else:
            text = f"🔍 *Результаты поиска:* `{query_text}`\n\n"
            
            for i, (chunk, score) in enumerate(results, 1):
                if score < 0.3:
                    continue
                
                emoji = "🎯" if score > 0.7 else "📌" if score > 0.5 else "📄"
                chunk_text = chunk['text'][:200]
                filename = chunk['filename']
                
                text += (
                    f"{emoji} *Результат {i}* ({score:.0%})\n"
                    f"📄 Источник: `{filename}`\n"
                    f"💬 {chunk_text}...\n\n"
                )
            
            text += "👇 Выберите действие:"
        
        keyboard = create_keyboard([
            ("🔍 Новый поиск", "rag_search"),
            ("« Назад", "rag_back_to_menu"),
        ], rows_per_row=2)
        
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="rag_search_results",
        )
        
        logger.info(f"RAG: User {user_id} search complete - {len([r for r in results if r[1] >= 0.3])} relevant results")
    
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        
        text = (
            f"❌ *Ошибка поиска*\n\n"
            f"{str(e)[:100]}\n\n"
            f"Попробуйте ещё раз."
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


@router.callback_query(F.data == "rag_stats")
async def cb_rag_stats(query: CallbackQuery, state: FSMContext) -> None:
    """Show RAG statistics."""
    user_id = query.from_user.id
    
    if user_id not in document_storage or not document_storage[user_id]:
        text = "📊 *Статистика*\n\nБаза знаний пуста."
    else:
        chunks = document_storage[user_id]
        unique_docs = set(c['filename'] for c in chunks)
        
        # Group by filename
        doc_chunks = {}
        for chunk in chunks:
            fname = chunk['filename']
            doc_chunks[fname] = doc_chunks.get(fname, 0) + 1
        
        text = (
            f"📊 *Статистика RAG*\n\n"
            f"📚 Документов: {len(unique_docs)}\n"
            f"📄 Фрагментов: {len(chunks)}\n"
            f"🧠 Embedding размер: 384D\n\n"
            f"*Документы:*\n"
        )
        
        for fname, count in sorted(doc_chunks.items()):
            text += f"  • `{fname}`: {count} фрагментов\n"
        
        text += "\n👇 Выберите действие:"
    
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


@router.callback_query(F.data == "rag_clear")
async def cb_rag_clear(query: CallbackQuery, state: FSMContext) -> None:
    """Clear RAG storage."""
    user_id = query.from_user.id
    
    if user_id in document_storage:
        count = len(document_storage[user_id])
        del document_storage[user_id]
        text = f"🗑️ *Очищено*\n\nУдалено {count} фрагментов из базы знаний.\n\n👇 Выберите действие:"
        logger.info(f"RAG: User {user_id} cleared {count} chunks")
    else:
        text = "📚 *База знаний*\n\nБаза уже пуста.\n\n👇 Выберите действие:"
    
    keyboard = create_keyboard([
        ("« Назад", "rag_back_to_menu"),
    ], rows_per_row=1)
    
    await MenuManager.navigate(
        callback=query,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=RAGStates.main_menu,
        screen_code="rag_clear",
        preserve_data=True,
    )


@router.callback_query(F.data == "rag_back_to_menu")
async def cb_rag_back_to_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Return to RAG main menu."""
    await show_rag_main_menu(callback=query, state=state)


@router.callback_query(F.data == "rag_cancel")
async def cb_rag_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Cancel RAG mode."""
    await state.clear()
    
    text = "❌ *Отменено*\n\nВозвращаемся в режим диалога."
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} exited RAG mode")
