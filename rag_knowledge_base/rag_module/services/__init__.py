"""RAG module services.

Core services for RAG pipeline:
  - chunker: Split documents into chunks
  - embeddings: Generate vector embeddings  
  - vector_store: ChromaDB wrapper
  - retriever: Semantic search
  - manager: Main RAG orchestrator (USE THIS!)

Quick Start:
    >>> from rag_module.services import RAGManager
    >>> manager = RAGManager()
    >>> doc = manager.add_document(Path("contract.pdf"), "doc_001")
    >>> results = manager.search("условия оплаты")
"""

from rag_module.services.chunker import Chunker, ChunkingError
from rag_module.services.embeddings import EmbeddingService, EmbeddingError
from rag_module.services.vector_store import ChromaVectorStore, VectorStoreError
from rag_module.services.retriever import Retriever, RetrieverError
from rag_module.services.manager import (
    RAGManager,
    RAGManagerError,
    DocumentNotFoundError,
)

__all__ = [
    # Main interface (USE THIS)
    "RAGManager",
    "RAGManagerError",
    "DocumentNotFoundError",
    # Individual services (for advanced usage)
    "Chunker",
    "ChunkingError",
    "EmbeddingService",
    "EmbeddingError",
    "ChromaVectorStore",
    "VectorStoreError",
    "Retriever",
    "RetrieverError",
]
