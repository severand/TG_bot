"""FSM states for RAG knowledge base functionality.

Added: 2025-12-21
Handles RAG workflow:
1. User activates RAG mode
2. User uploads documents to knowledge base
3. User performs semantic search
4. Bot returns relevant chunks from documents
"""

from aiogram.fsm.state import State, StatesGroup


class RAGStates(StatesGroup):
    """States for RAG knowledge base operations.
    
    States:
        main_menu: RAG main menu (upload or search)
        uploading: User uploading document to knowledge base
        searching: User entering search query
        processing: Currently processing RAG operation
    """
    
    main_menu = State()
    uploading = State()
    searching = State()
    processing = State()
