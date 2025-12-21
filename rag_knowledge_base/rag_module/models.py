"""Data models for RAG Knowledge Base Module.

Defines core data structures for documents, chunks, and search results.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid


@dataclass
class Document:
    """Represents a document in the knowledge base.
    
    Attributes:
        doc_id: Unique document identifier
        title: Human-readable document title
        file_path: Path to original file
        file_type: Document file type (pdf, docx, txt, etc.)
        file_size: File size in bytes
        content: Full text content of document
        created_at: Document upload timestamp
        updated_at: Last update timestamp
        metadata: Custom metadata dictionary
    """
    
    doc_id: str
    title: str
    file_path: Path
    file_type: str
    file_size: int
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary.
        
        Returns:
            Dictionary representation of document
        """
        data = asdict(self)
        data['file_path'] = str(data['file_path'])
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @property
    def chunk_count(self) -> int:
        """Estimate number of chunks (roughly by words/100).
        
        Returns:
            Estimated chunk count
        """
        word_count = len(self.content.split())
        return max(1, word_count // 100)


@dataclass
class Chunk:
    """Represents a text chunk with embedding.
    
    Attributes:
        chunk_id: Unique chunk identifier
        doc_id: Parent document ID
        text: Chunk text content
        position: Position in document (chunk number)
        page_number: Page number (for PDFs, optional)
        embedding: Vector embedding (384-dimensional)
        metadata: Custom metadata (source, position, etc.)
    """
    
    chunk_id: str
    doc_id: str
    text: str
    position: int
    embedding: Optional[List[float]] = None
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate chunk after initialization."""
        if not self.text or not self.text.strip():
            raise ValueError(f"Chunk text cannot be empty")
        
        if self.position < 0:
            raise ValueError(f"Chunk position must be non-negative, got {self.position}")
        
        if self.embedding is not None and len(self.embedding) != 384:
            raise ValueError(
                f"Embedding must be 384-dimensional, got {len(self.embedding)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'chunk_id': self.chunk_id,
            'doc_id': self.doc_id,
            'text': self.text,
            'position': self.position,
            'page_number': self.page_number,
            'metadata': self.metadata,
        }
    
    @property
    def text_length(self) -> int:
        """Get text length in characters.
        
        Returns:
            Character count
        """
        return len(self.text)
    
    @property
    def word_count(self) -> int:
        """Get text length in words.
        
        Returns:
            Word count
        """
        return len(self.text.split())


@dataclass
class SearchResult:
    """Represents a search result.
    
    Attributes:
        chunk_id: ID of matched chunk
        doc_id: ID of source document
        text: Chunk text
        similarity_score: Similarity score (0-1)
        source_doc: Human-readable document name
        page_number: Page number if available
        position: Position in document
        metadata: Additional metadata
    """
    
    chunk_id: str
    doc_id: str
    text: str
    similarity_score: float
    source_doc: str
    page_number: Optional[int] = None
    position: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate result after initialization."""
        if not (0 <= self.similarity_score <= 1):
            raise ValueError(
                f"Similarity score must be in [0, 1], got {self.similarity_score}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'chunk_id': self.chunk_id,
            'doc_id': self.doc_id,
            'text': self.text,
            'similarity_score': self.similarity_score,
            'source_doc': self.source_doc,
            'page_number': self.page_number,
            'position': self.position,
            'metadata': self.metadata,
        }
    
    def __repr__(self) -> str:
        """String representation.
        
        Returns:
            Formatted string
        """
        return (
            f"SearchResult(doc='{self.source_doc}', "
            f"similarity={self.similarity_score:.3f}, "
            f"text={self.text[:50]}...)"
        )


@dataclass
class DocumentInfo:
    """Information about a stored document.
    
    Attributes:
        doc_id: Document ID
        title: Document title
        file_type: File type
        file_size: File size in bytes
        chunk_count: Number of chunks
        created_at: Upload timestamp
        updated_at: Last update timestamp
        metadata: Custom metadata
    """
    
    doc_id: str
    title: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'chunk_count': self.chunk_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata,
        }


@dataclass
class SearchQuery:
    """Represents a search query.
    
    Attributes:
        query_text: User's search query
        top_k: Number of results to return
        similarity_threshold: Minimum similarity threshold
        filters: Optional metadata filters
        metadata: Query metadata (timestamp, user_id, etc.)
    """
    
    query_text: str
    top_k: int = 5
    similarity_threshold: float = 0.3
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate query."""
        if not self.query_text or not self.query_text.strip():
            raise ValueError("Query text cannot be empty")
        
        if self.top_k <= 0:
            raise ValueError(f"top_k must be positive, got {self.top_k}")
        
        if not (0 <= self.similarity_threshold <= 1):
            raise ValueError(
                f"similarity_threshold must be in [0, 1], got {self.similarity_threshold}"
            )


@dataclass
class HealthStatus:
    """Health status of RAG system.
    
    Attributes:
        is_healthy: Overall health status
        components: Status of each component
        last_check: Last health check timestamp
        message: Status message
    """
    
    is_healthy: bool
    components: Dict[str, bool] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.utcnow)
    message: str = "OK"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'is_healthy': self.is_healthy,
            'components': self.components,
            'last_check': self.last_check.isoformat(),
            'message': self.message,
        }
