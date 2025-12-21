"""Tests for validation utilities."""

import pytest
from pathlib import Path

from rag_module.utils.validators import (
    validate_file_path,
    validate_doc_id,
    validate_query,
    validate_top_k,
    validate_similarity_threshold,
    validate_metadata,
    ValidationError,
)


class TestValidateFilePath:
    """Tests for file path validation."""
    
    def test_valid_file_path(self, temp_dir):
        """Test validation of valid file path."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_path(test_file)
        assert result == test_file
    
    def test_missing_file(self, temp_dir):
        """Test validation of missing file."""
        test_file = temp_dir / "missing.txt"
        
        with pytest.raises(ValidationError, match="File not found"):
            validate_file_path(test_file)
    
    def test_empty_file(self, temp_dir):
        """Test validation of empty file."""
        test_file = temp_dir / "empty.txt"
        test_file.touch()
        
        with pytest.raises(ValidationError, match="File is empty"):
            validate_file_path(test_file)


class TestValidateDocId:
    """Tests for document ID validation."""
    
    def test_valid_doc_id(self):
        """Test validation of valid doc_id."""
        assert validate_doc_id("doc_001") == "doc_001"
        assert validate_doc_id("test-document") == "test-document"
        assert validate_doc_id("DOC_123") == "DOC_123"
    
    def test_empty_doc_id(self):
        """Test validation of empty doc_id."""
        with pytest.raises(ValidationError):
            validate_doc_id("")
        
        with pytest.raises(ValidationError):
            validate_doc_id("   ")
    
    def test_invalid_characters(self):
        """Test validation with invalid characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_doc_id("doc#001")
        
        with pytest.raises(ValidationError):
            validate_doc_id("doc@test")


class TestValidateQuery:
    """Tests for query validation."""
    
    def test_valid_query(self):
        """Test validation of valid query."""
        assert validate_query("test query") == "test query"
        assert validate_query("  query  ") == "query"
    
    def test_empty_query(self):
        """Test validation of empty query."""
        with pytest.raises(ValidationError):
            validate_query("")
    
    def test_query_too_long(self):
        """Test validation of too long query."""
        long_query = "a" * 2000
        with pytest.raises(ValidationError, match="too long"):
            validate_query(long_query)


class TestValidateTopK:
    """Tests for top_k validation."""
    
    def test_valid_top_k(self):
        """Test validation of valid top_k."""
        assert validate_top_k(5) == 5
        assert validate_top_k(100) == 100
    
    def test_invalid_top_k(self):
        """Test validation of invalid top_k."""
        with pytest.raises(ValidationError):
            validate_top_k(0)
        
        with pytest.raises(ValidationError):
            validate_top_k(1000)


class TestValidateSimilarityThreshold:
    """Tests for similarity threshold validation."""
    
    def test_valid_threshold(self):
        """Test validation of valid threshold."""
        assert validate_similarity_threshold(0.5) == 0.5
        assert validate_similarity_threshold(0.0) == 0.0
        assert validate_similarity_threshold(1.0) == 1.0
    
    def test_invalid_threshold(self):
        """Test validation of invalid threshold."""
        with pytest.raises(ValidationError):
            validate_similarity_threshold(-0.1)
        
        with pytest.raises(ValidationError):
            validate_similarity_threshold(1.5)


class TestValidateMetadata:
    """Tests for metadata validation."""
    
    def test_valid_metadata(self):
        """Test validation of valid metadata."""
        metadata = {"key": "value", "number": 123}
        result = validate_metadata(metadata)
        assert result == metadata
    
    def test_invalid_value_type(self):
        """Test validation with invalid value type."""
        metadata = {"key": ["list", "not", "allowed"]}
        with pytest.raises(ValidationError):
            validate_metadata(metadata)
    
    def test_too_many_fields(self):
        """Test validation with too many fields."""
        metadata = {f"key_{i}": i for i in range(150)}
        with pytest.raises(ValidationError, match="Too many"):
            validate_metadata(metadata)
