# Integration Guide: RAG Module with TG_bot 🔌

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2025-12-21  

---

## 🚀 Overview

This guide explains how to integrate the RAG Knowledge Base module into the main TG_bot project.

**Architecture:**
```
TG_bot (main project)
  ├── app/
  │   ├── handlers/knowledge.py          # ← NEW (Telegram command handlers)
  │   ├── states/knowledge.py            # ← NEW (FSM states)
  │   └── config.py                      # Update (add RAG config)
  │
  ├── main.py                         # Update (register handler)
  ├── requirements.txt                # Update (add RAG dependencies)
  │
  └── rag_knowledge_base/             # ← NEW (RAG module, submodule)
      ├── rag_module/
      ├── requirements.txt
      └── README.md
```

---

## 🔧 Step 1: Setup RAG Module (Already Done)

✅ The RAG module is created in the `rag_knowledge_base/` directory as a separate, reusable module.

**Verify structure:**
```bash
cd rag_knowledge_base
ls -la
# Should show: README.md, ARCHITECTURE.md, DEVELOPMENT.md, requirements.txt, rag_module/
```

---

## 🔧 Step 2: Install RAG Dependencies

### Option A: Shared Dependencies (Recommended)

Add RAG requirements to main project:

```bash
# Copy RAG dependencies to main requirements.txt
cat rag_knowledge_base/requirements.txt >> requirements.txt

# Remove duplicates
sort requirements.txt | uniq > requirements.tmp
mv requirements.tmp requirements.txt

# Install
pip install -r requirements.txt
```

### Option B: Separate Installation

```bash
# Install RAG dependencies separately
cd rag_knowledge_base
pip install -r requirements.txt
cd ..
```

**Verify installation:**
```python
import chromadb
import sentence_transformers
from rag_module.manager import RAGManager
print("✅ RAG module ready")
```

---

## 🔧 Step 3: Create Telegram Handler

Create `app/handlers/knowledge.py`:

```python
"""Knowledge base command handler.

Implements /knowledge command for document management and semantic search.
"""

import logging
from typing import Optional
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.enums import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.states.knowledge import KnowledgeStates
from app.config import get_settings
from rag_module.manager import RAGManager

logger = logging.getLogger(__name__)

router = Router()
rag_manager: Optional[RAGManager] = None


async def get_rag_manager() -> RAGManager:
    """Get or create RAG manager instance.
    
    Returns:
        RAGManager instance
    """
    global rag_manager
    if rag_manager is None:
        rag_manager = RAGManager()
    return rag_manager


def get_main_menu() -> InlineKeyboardMarkup:
    """Create main menu keyboard.
    
    Returns:
        Inline keyboard with menu options
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Add Document", callback_data="kb_add_doc"),
            InlineKeyboardButton(text="🔍 Search", callback_data="kb_search"),
        ],
        [
            InlineKeyboardButton(text="📑 List Documents", callback_data="kb_list"),
            InlineKeyboardButton(text="🛡️ Manage", callback_data="kb_manage"),
        ],
    ])


@router.message(Command("knowledge"))
async def knowledge_command(
    message: Message,
    state: FSMContext
) -> None:
    """Start knowledge base management.
    
    Args:
        message: User message
        state: FSM state
    """
    await state.clear()
    
    await message.answer(
        text=(
            "🧠 <b>Knowledge Base</b>\n\n"
            "Store documents and search them with AI\n\n"
            "<b>Features:</b>\n"
            "✅ Upload PDF, DOCX, TXT files\n"
            "✅ Semantic search across documents\n"
            "✅ 85-90% savings on API tokens\n"
        ),
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "kb_add_doc")
async def add_document(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle add document action.
    
    Args:
        callback: Callback query
        state: FSM state
    """
    await state.set_state(KnowledgeStates.waiting_for_document)
    
    await callback.message.edit_text(
        text=(
            "📄 <b>Add Document</b>\n\n"
            "Send a document file (PDF, DOCX, TXT)\n\n"
            "<b>Max file size:</b> 20MB\n"
            "<b>Supported formats:</b>\n"
            "• PDF\n"
            "• DOCX (Word)\n"
            "• TXT (Text)\n"
        ),
        parse_mode="HTML",
        reply_markup=None
    )


@router.message(
    KnowledgeStates.waiting_for_document,
    F.content_type.in_({ContentType.DOCUMENT})
)
async def process_document(
    message: Message,
    state: FSMContext
) -> None:
    """Process uploaded document.
    
    Args:
        message: Message with document
        state: FSM state
    """
    try:
        # Show processing message
        status_msg = await message.answer(
            text="🔄 Processing document...\n"
                 "- Downloading file\n"
                 "- Extracting text\n"
                 "- Creating embeddings\n"
                 "- Storing in knowledge base"
        )
        
        # Download file
        settings = get_settings()
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(exist_ok=True)
        
        file_info = await message.bot.get_file(message.document.file_id)
        file_path = temp_dir / message.document.file_name
        await message.bot.download_file(file_info.file_path, file_path)
        
        # Add to knowledge base
        manager = await get_rag_manager()
        doc_info = await manager.add_document(
            file_path=file_path,
            doc_id=f"doc_{message.from_user.id}_{file_path.stem}"
        )
        
        # Show success
        await status_msg.edit_text(
            text=(
                "✅ <b>Document Added!</b>\n\n"
                f"<b>Title:</b> {doc_info.title}\n"
                f"<b>Size:</b> {doc_info.file_size / 1024:.1f} KB\n"
                f"<b>Chunks:</b> {doc_info.chunk_count}\n\n"
                "Now you can search it with /knowledge command"
            ),
            parse_mode="HTML"
        )
        
        # Cleanup
        file_path.unlink()
        
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        await status_msg.edit_text(
            text=f"❌ <b>Error:</b> {str(e)}",
            parse_mode="HTML"
        )
    
    await state.clear()


@router.callback_query(F.data == "kb_search")
async def search_knowledge(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle search action.
    
    Args:
        callback: Callback query
        state: FSM state
    """
    await state.set_state(KnowledgeStates.waiting_for_query)
    
    await callback.message.edit_text(
        text=(
            "🔍 <b>Search Knowledge Base</b>\n\n"
            "Type your question and I'll search the documents."
        ),
        parse_mode="HTML",
        reply_markup=None
    )


@router.message(KnowledgeStates.waiting_for_query)
async def process_query(
    message: Message,
    state: FSMContext
) -> None:
    """Process search query.
    
    Args:
        message: Message with query
        state: FSM state
    """
    try:
        # Show searching message
        search_msg = await message.answer(
            text="🔍 Searching knowledge base..."
        )
        
        # Search
        manager = await get_rag_manager()
        results = await manager.search(
            query=message.text,
            top_k=3
        )
        
        # Format results
        if not results:
            answer = "퉴 No relevant documents found."
        else:
            answer = "<b>🔍 Search Results:</b>\n\n"
            for i, result in enumerate(results, 1):
                answer += f"<b>{i}. {result.source_doc}</b>\n"
                answer += f"Relevance: {result.similarity_score*100:.1f}%\n"
                answer += f"<code>{result.text[:200]}...</code>\n\n"
        
        await search_msg.edit_text(
            text=answer,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error searching: {e}", exc_info=True)
        await search_msg.edit_text(
            text=f"❌ Error: {str(e)}"
        )
    
    await state.clear()


@router.callback_query(F.data == "kb_list")
async def list_documents(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """List all documents.
    
    Args:
        callback: Callback query
        state: FSM state
    """
    try:
        manager = await get_rag_manager()
        docs = await manager.list_documents()
        
        if not docs:
            text = "📄 <b>Documents:</b>\n\nNo documents yet. Use 'Add Document' to get started."
        else:
            text = "📄 <b>Your Documents:</b>\n\n"
            for doc in docs:
                text += f"<b>{doc.title}</b>\n"
                text += f"Size: {doc.file_size/1024:.1f}KB | Chunks: {doc.chunk_count}\n"
                text += f"Added: {doc.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        await callback.answer(
            text=f"Error: {str(e)}",
            show_alert=True
        )
```

---

## 🔧 Step 4: Create FSM States

Create `app/states/knowledge.py`:

```python
"""FSM states for knowledge base handler."""

from aiogram.fsm.state import StatesGroup, State


class KnowledgeStates(StatesGroup):
    """States for knowledge base operations."""
    
    waiting_for_document = State()  # User uploading a document
    waiting_for_query = State()     # User entering search query
```

---

## 🔧 Step 5: Register Handler in main.py

Update `main.py`:

```python
# At the top, add import:
from app.handlers import knowledge

# In main() function, add handler registration (before common.router):
dispatcher.include_router(knowledge.router)  # Add BEFORE common.router

# Make sure order is:
# 1. homework.router
# 2. prompts.router
# 3. conversation.router
# 4. chat.router
# 5. knowledge.router        <-- NEW, add here
# 6. documents.router
# 7. common.router           <-- MUST be last
```

---

## 🔧 Step 6: Update Main Requirements

Update main project's `requirements.txt`:

```bash
# Add RAG dependencies
chromadb==0.5.0
sentence-transformers==3.0.1
PyPDF2==4.0.1
python-docx==1.0.1

# Keep existing dependencies...
```

---

## 🔧 Step 7: Configuration

Add to main project's `app/config.py`:

```python
# Add at top:
from pathlib import Path

# Add to Settings class:
class Settings(BaseSettings):
    # ... existing settings ...
    
    # RAG Configuration
    VECTOR_DB_PATH: str = "./data/vector_db"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
```

---

## 🔧 Step 8: Test Integration

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py

# In Telegram:
# 1. Send /knowledge
# 2. Click "Add Document"
# 3. Upload a PDF or DOCX file
# 4. Click "Search"
# 5. Ask a question
```

---

## 🔧 Step 9: Production Checklist

Before deploying:

- [ ] RAG module installed (`pip install rag_knowledge_base`)
- [ ] Handler registered in `main.py`
- [ ] FSM states created
- [ ] Configuration set via environment variables
- [ ] Vector database directory writable
- [ ] Dependencies installed
- [ ] Tests passing
- [ ] Error handling working
- [ ] Logging configured
- [ ] Documentation updated

---

## 🚁 Troubleshooting

### "RAG module not found" error
```bash
# Solution: Install RAG dependencies
pip install chromadb sentence-transformers PyPDF2 python-docx
```

### Handler not responding
```python
# Check: handler registered BEFORE common.router in main.py
# Order matters!
```

### Documents not searchable
```python
# Check: Vector DB path writable
# Check: ChromaDB persisting data
# Check: Embeddings generated successfully
```

### Memory issues with large documents
```python
# Solution: Adjust CHUNK_SIZE and EMBEDDING_BATCH_SIZE
# Smaller chunks = less memory per chunk
```

---

## 🚅 Next Steps

1. **Implement core RAG services** (chunker, embeddings, vector store, etc.)
2. **Write tests** for integration
3. **Add performance monitoring**
4. **Create web interface** for document management
5. **Add advanced features** (metadata filtering, versioning, etc.)

---

**Status:** Ready for handler implementation  
**Last Updated:** 2025-12-21  
**Maintainer:** Project Owner
