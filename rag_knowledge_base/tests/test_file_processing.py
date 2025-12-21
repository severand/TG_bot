"""Tests for file processing components."""

import pytest
from pathlib import Path

from rag_module.file_processing.text_cleaner import TextCleaner


class TestTextCleaner:
    """Tests for TextCleaner utility."""
    
    def test_clean_basic_text(self):
        """Test cleaning basic text."""
        text = "This is   a    test   text."
        cleaned = TextCleaner.clean_extracted_text(text)
        
        assert "test" in cleaned
        assert "   " not in cleaned  # Multiple spaces removed
    
    def test_clean_empty_text(self):
        """Test cleaning empty text."""
        cleaned = TextCleaner.clean_extracted_text("")
        assert cleaned == ""
    
    def test_remove_control_chars(self):
        """Test removal of control characters."""
        text = "Hello\x00World\x01Test"
        cleaned = TextCleaner.clean_extracted_text(text)
        
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "Hello" in cleaned
    
    def test_is_text_usable(self):
        """Test text quality check."""
        good_text = "This is a good quality text with enough content."
        assert TextCleaner.is_text_usable(good_text)
        
        bad_text = "12345"
        assert not TextCleaner.is_text_usable(bad_text, min_length=50)
    
    def test_get_preview(self):
        """Test text preview generation."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"
        preview = TextCleaner.get_preview(text, max_lines=3)
        
        assert "Line 1" in preview
        assert "Line 2" in preview
        assert "Line 3" in preview


# Note: Tests for PDF/DOCX parsers would require test files
@pytest.mark.integration
class TestParsers:
    """Tests for file parsers (require test files)."""
    
    def test_pdf_parser(self, temp_dir):
        """Test PDF parser."""
        pytest.skip("Requires test PDF file")
    
    def test_docx_parser(self, temp_dir):
        """Test DOCX parser."""
        pytest.skip("Requires test DOCX file")
