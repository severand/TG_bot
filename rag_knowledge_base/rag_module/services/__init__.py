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

# Lazy imports for ChromaDB-dependent modules to avoid DLL issues on import
def __getattr__(name):
    if name == "ChromaVectorStore":
        from rag_module.services.vector_store import ChromaVectorStore
        return ChromaVectorStore
    elif name == "VectorStoreError":
        from rag_module.services.vector_store import VectorStoreError
        return VectorStoreError
    elif name == "Retriever":
        from rag_module.services.retriever import Retriever
        return Retriever
    elif name == "RetrieverError":
        from rag_module.services.retriever import RetrieverError
        return RetrieverError
    elif name == "RAGManager":
        from rag_module.services.manager import RAGManager
        return RAGManager
    elif name == "RAGManagerError":
        from rag_module.services.manager import RAGManagerError
        return RAGManagerError
    elif name == "DocumentNotFoundError":
        from rag_module.services.manager import DocumentNotFoundError
        return DocumentNotFoundError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
