"""Unit tests for file processing module.

Tests for DOCX/DOC parser, file converter, and error handling.

Added: 2025-12-20 23:57
"""

import pytest
from pathlib import Path
from io import BytesIO
import zipfile
from unittest.mock import Mock, patch, MagicMock

from app.services.file_processing.docx_parser import DOCXParser
from app.services.file_processing.converter import FileConverter


class TestDOCXParser:
    """Tests for DOCX parser."""
    
    @pytest.fixture
    def parser(self):
        """Create DOCX parser instance."""
        return DOCXParser()
    
    @pytest.fixture
    def temp_docx_file(self, tmp_path):
        """Create a test DOCX file."""
        # Create a minimal valid DOCX file (ZIP with XML)
        docx_path = tmp_path / "test.docx"
        
        with zipfile.ZipFile(docx_path, 'w') as zf:
            # Add document.xml with test content
            doc_xml = '''<?xml version="1.0"?>
<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <body>
        <p><r><t>Test paragraph content</t></r></p>
        <p><r><t>Another paragraph</t></r></p>
    </body>
</document>
'''
            zf.writestr('word/document.xml', doc_xml)
            zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
        
        return docx_path
    
    def test_extract_text_from_valid_docx(self, parser, temp_docx_file):
        """Test extraction from valid DOCX file."""
        text = parser.extract_text(temp_docx_file)
        
        assert text is not None
        assert len(text) > 0
        assert "Test paragraph content" in text or "Another paragraph" in text
    
    def test_extract_text_file_not_found(self, parser, tmp_path):
        """Test extraction from non-existent file."""
        fake_file = tmp_path / "nonexistent.docx"
        
        with pytest.raises(FileNotFoundError):
            parser.extract_text(fake_file)
    
    def test_extract_text_invalid_docx(self, parser, tmp_path):
        """Test extraction from invalid DOCX file."""
        # Create invalid DOCX (not a ZIP)
        invalid_file = tmp_path / "invalid.docx"
        invalid_file.write_text("This is not a valid DOCX file")
        
        # Should handle gracefully and return empty or raise ValueError
        try:
            result = parser.extract_text(invalid_file)
            # If it doesn't raise, it should return empty string
            assert result == ""
        except ValueError:
            # This is also acceptable
            pass
    
    def test_extract_text_empty_docx(self, parser, tmp_path):
        """Test extraction from empty DOCX."""
        empty_docx = tmp_path / "empty.docx"
        
        with zipfile.ZipFile(empty_docx, 'w') as zf:
            doc_xml = '''<?xml version="1.0"?>
<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <body></body>
</document>
'''
            zf.writestr('word/document.xml', doc_xml)
            zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
        
        text = parser.extract_text(empty_docx)
        
        # Empty document should return empty or near-empty string
        assert text == "" or len(text.strip()) == 0
    
    def test_extract_plain_text_from_corrupted_xml(self):
        """Test extraction from corrupted XML."""
        corrupted = "<tag>Hello</tag> <tag>World</tag> <corrupted>Incomplete"
        
        result = DOCXParser._extract_plain_text_from_corrupted_xml(corrupted)
        
        assert "Hello" in result
        assert "World" in result
        assert result.strip()  # Should have some content
    
    def test_get_metadata(self, parser, temp_docx_file):
        """Test metadata extraction."""
        metadata = parser.get_metadata(temp_docx_file)
        
        assert isinstance(metadata, dict)
        # Metadata keys should exist even if values are None
        # (python-docx returns None for missing metadata)


class TestFileConverter:
    """Tests for file converter."""
    
    @pytest.fixture
    def converter(self):
        """Create file converter instance."""
        return FileConverter()
    
    def test_is_supported_pdf(self, converter):
        """Test PDF format is supported."""
        assert converter.is_supported(Path("document.pdf"))
    
    def test_is_supported_docx(self, converter):
        """Test DOCX format is supported."""
        assert converter.is_supported(Path("document.docx"))
    
    def test_is_supported_doc(self, converter):
        """Test DOC format is supported."""
        assert converter.is_supported(Path("document.doc"))
    
    def test_is_supported_xlsx(self, converter):
        """Test XLSX format is supported."""
        assert converter.is_supported(Path("spreadsheet.xlsx"))
    
    def test_is_supported_xls(self, converter):
        """Test XLS format is supported."""
        assert converter.is_supported(Path("spreadsheet.xls"))
    
    def test_is_supported_txt(self, converter):
        """Test TXT format is supported."""
        assert converter.is_supported(Path("document.txt"))
    
    def test_is_supported_zip(self, converter):
        """Test ZIP format is supported."""
        assert converter.is_supported(Path("archive.zip"))
    
    def test_is_supported_unsupported_format(self, converter):
        """Test unsupported format is rejected."""
        assert not converter.is_supported(Path("image.jpg"))
        assert not converter.is_supported(Path("video.mp4"))
    
    def test_extract_text_file_not_found(self, converter, tmp_path):
        """Test extraction from non-existent file."""
        fake_file = tmp_path / "nonexistent.docx"
        
        with pytest.raises(FileNotFoundError):
            converter.extract_text(fake_file)
    
    def test_extract_text_unsupported_format(self, converter, tmp_path):
        """Test extraction from unsupported format."""
        unsupported = tmp_path / "image.jpg"
        unsupported.write_text("fake image")
        
        with pytest.raises(ValueError, match="Unsupported format"):
            converter.extract_text(unsupported)
    
    def test_extract_text_txt_file(self, converter, tmp_path):
        """Test extraction from plain text file."""
        txt_file = tmp_path / "test.txt"
        content = "This is a test file\nWith multiple lines"
        txt_file.write_text(content)
        
        result = converter.extract_text(txt_file)
        
        assert result == content
    
    @patch('app.services.file_processing.converter.PDFParser')
    def test_extract_text_pdf_delegated_to_parser(self, mock_pdf_parser_class, converter, tmp_path):
        """Test that PDF extraction is delegated to PDFParser."""
        # Setup mock
        mock_parser = MagicMock()
        mock_parser.extract_text.return_value = "PDF content"
        mock_pdf_parser_class.return_value = mock_parser
        
        # Create PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        # Create new converter to use mocked PDF parser
        converter_with_mock = FileConverter()
        converter_with_mock.pdf_parser = mock_parser
        
        result = converter_with_mock.extract_text(pdf_file)
        
        # Verify parser was called
        mock_parser.extract_text.assert_called_once()
        assert result == "PDF content"
    
    def test_supported_formats_complete(self, converter):
        """Test that all expected formats are in supported list."""
        from app.services.file_processing.converter import SUPPORTED_FORMATS
        
        expected = {".pdf", ".docx", ".txt", ".zip", ".doc", ".xlsx", ".xls"}
        assert SUPPORTED_FORMATS == expected


class TestDOCToDocxConversion:
    """Tests for DOC to DOCX conversion."""
    
    @pytest.fixture
    def converter(self):
        """Create file converter instance."""
        return FileConverter()
    
    def test_doc_file_detection(self, converter):
        """Test that .doc files are recognized."""
        assert converter.is_supported(Path("document.doc"))
    
    def test_rename_doc_to_docx_success(self, converter, tmp_path):
        """Test successful .doc to .docx rename."""
        # Create a minimal valid Office file (ZIP)
        doc_file = tmp_path / "test.doc"
        with zipfile.ZipFile(doc_file, 'w') as zf:
            zf.writestr('word/document.xml', '<?xml version="1.0"?><document/>')
        
        # Rename should work
        docx_path = converter._rename_doc_to_docx(doc_file, tmp_path)
        
        assert docx_path is not None
        assert docx_path.suffix == ".docx"
        assert docx_path.exists()
    
    def test_rename_doc_permissions_error(self, converter, tmp_path):
        """Test .doc rename when permissions denied."""
        doc_file = tmp_path / "test.doc"
        doc_file.write_text("test")
        
        # Mock shutil.copy2 to raise permission error
        with patch('shutil.copy2', side_effect=PermissionError):
            result = converter._rename_doc_to_docx(doc_file, tmp_path)
            assert result is None  # Should return None on error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
