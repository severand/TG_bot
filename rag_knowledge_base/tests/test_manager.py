"""Tests for RAGManager - main orchestrator."""

import pytest
from pathlib import Path

from rag_module.services.manager import RAGManager, RAGManagerError, DocumentNotFoundError


class TestRAGManagerBasic:
    """Basic tests for RAGManager."""
    
    def test_init(self, temp_dir):
        """Test manager initialization."""
        manager = RAGManager()
        assert manager is not None
        assert manager.file_converter is not None
        assert manager.chunker is not None
    
    def test_get_stats_empty(self, temp_dir):
        """Test getting stats from empty system."""
        manager = RAGManager()
        stats = manager.get_stats()
        
        assert stats["total_documents"] == 0
        assert "embedding_dimension" in stats
        assert "similarity_threshold" in stats
    
    def test_list_documents_empty(self, temp_dir):
        """Test listing documents when empty."""
        manager = RAGManager()
        docs = manager.list_documents()
        assert len(docs) == 0
    
    def test_get_nonexistent_document(self, temp_dir):
        """Test getting non-existent document."""
        manager = RAGManager()
        with pytest.raises(DocumentNotFoundError):
            manager.get_document("nonexistent_id")
    
    def test_delete_nonexistent_document(self, temp_dir):
        """Test deleting non-existent document."""
        manager = RAGManager()
        with pytest.raises(DocumentNotFoundError):
            manager.delete_document("nonexistent_id")


class TestRAGManagerSearch:
    """Tests for search functionality."""
    
    def test_search_empty_query(self, temp_dir):
        """Test search with empty query."""
        manager = RAGManager()
        results = manager.search("")
        assert len(results) == 0
    
    def test_search_no_documents(self, temp_dir):
        """Test search when no documents exist."""
        manager = RAGManager()
        results = manager.search("test query")
        # Should not crash, just return empty
        assert isinstance(results, list)


# Note: Full integration tests with actual document loading
# would require test documents and are marked as integration tests
@pytest.mark.integration
class TestRAGManagerIntegration:
    """Integration tests for RAGManager (require dependencies)."""
    
    def test_add_search_cycle(self, temp_dir, sample_text):
        """Test full add -> search cycle."""
        # This test requires embeddings and vector store
        pytest.skip("Requires sentence-transformers and chromadb")
