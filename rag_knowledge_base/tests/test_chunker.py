"""Tests for Chunker service."""

import pytest
from rag_module.services.chunker import Chunker, ChunkingError


class TestChunker:
    """Tests for Chunker class."""
    
    def test_init_default(self):
        """Test chunker initialization with defaults."""
        chunker = Chunker()
        assert chunker.chunk_size > 0
        assert chunker.chunk_overlap >= 0
    
    def test_init_custom(self):
        """Test chunker initialization with custom values."""
        chunker = Chunker(chunk_size=100, chunk_overlap=20)
        assert chunker.chunk_size == 100
        assert chunker.chunk_overlap == 20
    
    def test_chunk_text_basic(self, sample_text, sample_doc_id):
        """Test basic text chunking."""
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk_text(sample_text, sample_doc_id)
        
        assert len(chunks) > 0
        assert all(chunk.doc_id == sample_doc_id for chunk in chunks)
        assert all(chunk.text for chunk in chunks)
        assert all(chunk.position >= 0 for chunk in chunks)
    
    def test_chunk_text_empty(self, sample_doc_id):
        """Test chunking empty text."""
        chunker = Chunker()
        chunks = chunker.chunk_text("", sample_doc_id)
        assert len(chunks) == 0
    
    def test_chunk_text_with_metadata(self, sample_text, sample_doc_id, sample_metadata):
        """Test chunking with metadata."""
        chunker = Chunker()
        chunks = chunker.chunk_text(sample_text, sample_doc_id, base_metadata=sample_metadata)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata is not None
            assert "type" in chunk.metadata
            assert chunk.metadata["type"] == "test"
    
    def test_chunk_overlap(self, sample_doc_id):
        """Test that overlap works correctly."""
        text = " ".join([f"word{i}" for i in range(100)])
        chunker = Chunker(chunk_size=20, chunk_overlap=5)
        chunks = chunker.chunk_text(text, sample_doc_id)
        
        # Should have multiple chunks with overlap
        assert len(chunks) > 1
    
    def test_invalid_chunk_size(self):
        """Test initialization with invalid chunk size."""
        with pytest.raises(ChunkingError):
            Chunker(chunk_size=0)
        
        with pytest.raises(ChunkingError):
            Chunker(chunk_size=-10)
    
    def test_invalid_overlap(self):
        """Test initialization with invalid overlap."""
        with pytest.raises(ChunkingError):
            Chunker(chunk_size=100, chunk_overlap=100)
        
        with pytest.raises(ChunkingError):
            Chunker(chunk_size=100, chunk_overlap=150)
