"""Custom exceptions for RAG Knowledge Base Module.

Defines hierarchy of exceptions for better error handling.
"""


class RAGException(Exception):
    """Base exception for RAG module.
    
    All RAG-specific exceptions should inherit from this.
    """
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        """Initialize RAG exception.
        
        Args:
            message: Error message
            error_code: Error code for programmatic handling
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def __repr__(self) -> str:
        """String representation.
        
        Returns:
            Exception details
        """
        return f"{self.__class__.__name__}(code={self.error_code}, msg={self.message})"


class FileProcessingError(RAGException):
    """Raised when document file processing fails.
    
    Causes:
        - File not found
        - Invalid file format
        - Corrupted file
        - Permission denied
    """
    
    def __init__(self, message: str, file_path: str = None):
        """Initialize file processing error.
        
        Args:
            message: Error message
            file_path: Path to problematic file
        """
        self.file_path = file_path
        super().__init__(message, "FILE_PROCESSING_ERROR")


class ChunkingError(RAGException):
    """Raised when document chunking fails.
    
    Causes:
        - Invalid chunk size
        - Empty document
        - Memory exhaustion
    """
    
    def __init__(self, message: str):
        """Initialize chunking error.
        
        Args:
            message: Error message
        """
        super().__init__(message, "CHUNKING_ERROR")


class EmbeddingError(RAGException):
    """Raised when embedding generation fails.
    
    Causes:
        - Model not found or corrupted
        - CUDA out of memory
        - Invalid input text
        - Network error (downloading model)
    """
    
    def __init__(self, message: str, batch_size: int = None):
        """Initialize embedding error.
        
        Args:
            message: Error message
            batch_size: Batch size that caused error (if applicable)
        """
        self.batch_size = batch_size
        super().__init__(message, "EMBEDDING_ERROR")


class VectorStoreError(RAGException):
    """Raised when vector database operations fail.
    
    Causes:
        - Database corrupted
        - Disk full
        - Permission denied
        - Dimension mismatch
    """
    
    def __init__(self, message: str, operation: str = None):
        """Initialize vector store error.
        
        Args:
            message: Error message
            operation: Database operation that failed (add, search, delete)
        """
        self.operation = operation
        super().__init__(message, "VECTOR_STORE_ERROR")


class RetrieverError(RAGException):
    """Raised when semantic search fails.
    
    Causes:
        - Vector store not initialized
        - Query embedding failed
        - No results found
        - Invalid query
    """
    
    def __init__(self, message: str, query: str = None):
        """Initialize retriever error.
        
        Args:
            message: Error message
            query: Query that caused error
        """
        self.query = query
        super().__init__(message, "RETRIEVER_ERROR")


class ConfigurationError(RAGException):
    """Raised when configuration is invalid.
    
    Causes:
        - Missing required environment variables
        - Invalid configuration values
        - Conflicting settings
    """
    
    def __init__(self, message: str, config_key: str = None):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused error
        """
        self.config_key = config_key
        super().__init__(message, "CONFIGURATION_ERROR")


class DocumentNotFoundError(RAGException):
    """Raised when document doesn't exist in knowledge base.
    
    Causes:
        - Document ID doesn't exist
        - Document was deleted
        - Typo in document ID
    """
    
    def __init__(self, message: str, doc_id: str = None):
        """Initialize document not found error.
        
        Args:
            message: Error message
            doc_id: Document ID that wasn't found
        """
        self.doc_id = doc_id
        super().__init__(message, "DOCUMENT_NOT_FOUND")


class LLMIntegrationError(RAGException):
    """Raised when LLM integration fails.
    
    Causes:
        - LLM API unreachable
        - Invalid API key
        - Rate limit exceeded
        - LLM error in processing
    """
    
    def __init__(self, message: str):
        """Initialize LLM integration error.
        
        Args:
            message: Error message
        """
        super().__init__(message, "LLM_INTEGRATION_ERROR")


class ValidationError(RAGException):
    """Raised when input validation fails.
    
    Causes:
        - Invalid parameter values
        - Missing required fields
        - Type mismatch
    """
    
    def __init__(self, message: str, field_name: str = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            field_name: Field that failed validation
        """
        self.field_name = field_name
        super().__init__(message, "VALIDATION_ERROR")
