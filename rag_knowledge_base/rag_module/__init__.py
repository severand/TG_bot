"""RAG Knowledge Base Module.

Retrieval-Augmented Generation system for document-based question answering.

Key Components:
    - FileProcessor: Extract text from various document formats
    - Chunker: Split documents into semantic chunks
    - EmbeddingService: Generate vector embeddings
    - VectorStore: Persist embeddings in ChromaDB
    - Retriever: Semantic search in knowledge base
    - RAGManager: Orchestrate all components

Quick Start:
    from rag_module.manager import RAGManager
    
    manager = RAGManager()
    
    # Add document
    await manager.add_document(
        file_path="document.pdf",
        doc_id="doc_2024"
    )
    
    # Search
    results = await manager.search(
        query="What are the main points?",
        top_k=3
    )

Version: 1.0.0
Status: In Development
License: Same as TG_bot project
"""

__version__ = "1.0.0"
__author__ = "Project Owner"
__license__ = "MIT"

from rag_module.config import RAGConfig
from rag_module.models import Document, Chunk, SearchResult, DocumentInfo
from rag_module.exceptions import RAGException
from rag_module.manager import RAGManager

__all__ = [
    "RAGConfig",
    "Document",
    "Chunk",
    "SearchResult",
    "DocumentInfo",
    "RAGException",
    "RAGManager",
]
