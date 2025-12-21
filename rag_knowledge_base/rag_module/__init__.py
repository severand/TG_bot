"""RAG (Retrieval-Augmented Generation) Knowledge Base Module.

Standalone module for document-based question answering.
Provides document management, semantic search, and LLM integration.

Core Components:
  - file_processing: Parse PDF, DOCX, TXT, XLS, DOC, ZIP files
  - services: Core RAG services (chunker, embeddings, vector store, retriever)
  - models: Data models (Document, Chunk, SearchResult)
  - exceptions: Custom exception hierarchy
  - config: Configuration management

Quick Start:
    >>> from rag_module.services import RAGManager
    >>> manager = RAGManager()
    >>> doc = manager.add_document("contract.pdf", "doc_001")
    >>> results = manager.search("payment terms")
"""

from rag_module.config import RAGConfig, get_config, set_config
from rag_module.models import Document, Chunk, SearchResult
from rag_module.exceptions import RAGException
from rag_module.file_processing import FileConverter, PDFParser, DOCXParser

__version__ = "1.0.0"
__all__ = [
    "RAGConfig",
    "get_config",
    "set_config",
    "Document",
    "Chunk",
    "SearchResult",
    "RAGException",
    "FileConverter",
    "PDFParser",
    "DOCXParser",
]
