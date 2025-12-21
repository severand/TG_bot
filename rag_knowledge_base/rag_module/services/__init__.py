"""RAG module services.

Core services for RAG pipeline:
  - chunker: Split documents into chunks
  - embeddings: Generate vector embeddings
  - vector_store: ChromaDB wrapper
  - retriever: Semantic search
  - file_processor: Extract text from documents
  - manager: Orchestrate all services
"""

from rag_module.services.chunker import Chunker, ChunkingError

__all__ = [
    "Chunker",
    "ChunkingError",
]
