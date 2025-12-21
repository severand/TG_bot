"""Configuration for RAG Knowledge Base Module.

Loads settings from environment variables with sensible defaults.
Use environment variables to override defaults.

Example:
    export VECTOR_DB_PATH=./data/vector_db
    export CHUNK_SIZE=500
    export TOP_K_RESULTS=5
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from os import getenv
import logging

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuration for RAG module.
    
    Attributes:
        vector_db_path: Path to vector database directory
        temp_dir: Path for temporary files
        embedding_model: Sentence-Transformers model name
        embedding_device: Device for embeddings (cpu, cuda, mps)
        chunk_size: Maximum chunk size in tokens/words
        chunk_overlap: Overlap between chunks
        top_k: Default number of results to return
        similarity_threshold: Minimum similarity score (0-1)
        llm_max_tokens: Max tokens for LLM responses
        llm_temperature: Temperature for LLM (0-2)
        debug: Enable debug logging
        use_cache: Use caching for embeddings
        cache_size: Size of embedding cache
    """
    
    # Paths
    vector_db_path: Path = field(
        default_factory=lambda: Path(getenv('VECTOR_DB_PATH', './data/vector_db'))
    )
    temp_dir: Path = field(
        default_factory=lambda: Path(getenv('TEMP_DIR', './temp'))
    )
    
    # Embeddings
    embedding_model: str = getenv(
        'EMBEDDING_MODEL',
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    )
    embedding_device: str = getenv('EMBEDDING_DEVICE', 'cpu')
    embedding_batch_size: int = int(getenv('EMBEDDING_BATCH_SIZE', '32'))
    embedding_dimension: int = 384  # Fixed for paraphrase-MiniLM
    
    # Chunking
    chunk_size: int = int(getenv('CHUNK_SIZE', '500'))
    chunk_overlap: int = int(getenv('CHUNK_OVERLAP', '50'))
    
    # Retrieval
    top_k: int = int(getenv('TOP_K_RESULTS', '5'))
    similarity_threshold: float = float(getenv('SIMILARITY_THRESHOLD', '0.3'))
    
    # LLM Integration
    llm_max_tokens: int = int(getenv('LLM_MAX_TOKENS', '2000'))
    llm_temperature: float = float(getenv('LLM_TEMPERATURE', '0.7'))
    
    # Performance
    debug: bool = getenv('DEBUG', 'false').lower() == 'true'
    use_cache: bool = getenv('USE_CACHE', 'true').lower() == 'true'
    cache_size: int = int(getenv('CACHE_SIZE', '1000'))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Create directories if they don't exist
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate values
        if self.chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {self.chunk_size}")
        
        if self.chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be non-negative, got {self.chunk_overlap}")
        
        if not (0 <= self.similarity_threshold <= 1):
            raise ValueError(
                f"similarity_threshold must be in [0, 1], got {self.similarity_threshold}"
            )
        
        if not (0 <= self.llm_temperature <= 2):
            raise ValueError(
                f"llm_temperature must be in [0, 2], got {self.llm_temperature}"
            )
        
        if self.embedding_device not in ['cpu', 'cuda', 'mps']:
            raise ValueError(
                f"embedding_device must be one of [cpu, cuda, mps], "
                f"got {self.embedding_device}"
            )
        
        if self.debug:
            logger.info("DEBUG mode enabled")
            logger.debug(f"Configuration: {self}")
    
    @property
    def vector_db_chroma_path(self) -> Path:
        """Path to ChromaDB data directory."""
        return self.vector_db_path / "chroma_db"
    
    @property
    def metadata_path(self) -> Path:
        """Path to metadata file."""
        return self.vector_db_path / "metadata.json"
    
    @property
    def logs_path(self) -> Path:
        """Path to logs directory."""
        return self.vector_db_path / "logs"
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            'vector_db_path': str(self.vector_db_path),
            'temp_dir': str(self.temp_dir),
            'embedding_model': self.embedding_model,
            'embedding_device': self.embedding_device,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'top_k': self.top_k,
            'similarity_threshold': self.similarity_threshold,
            'llm_max_tokens': self.llm_max_tokens,
            'llm_temperature': self.llm_temperature,
            'debug': self.debug,
        }


# Global config instance
_config: Optional[RAGConfig] = None


def get_config() -> RAGConfig:
    """Get global RAG configuration.
    
    Returns:
        RAG configuration instance
    """
    global _config
    if _config is None:
        _config = RAGConfig()
    return _config


def set_config(config: RAGConfig) -> None:
    """Set global RAG configuration.
    
    Args:
        config: New configuration instance
    """
    global _config
    _config = config
    logger.info("RAG configuration updated")


def reset_config() -> None:
    """Reset configuration to defaults."""
    global _config
    _config = None
    logger.info("RAG configuration reset to defaults")
