"""Document parser using pandoc universal converter.

ОКОНЧАТЕЛЬНОЕ РЕШЕНИЕ 2025-12-21 13:19:
- pandoc - универсальный конвертер документов
- Поддерживает .doc, .docx, .pdf, .odt, .rtf и 150+ других
- НЕ нужны хаки, РАБОТАЕТ

Setup:
- Windows: choco install pandoc
- Linux: apt-get install pandoc  
- macOS: brew install pandoc
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from app.services.file_processing.text_cleaner import TextCleaner

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

logger = logging.getLogger(__name__)


def _get_text_preview(text: str, max_words: int = 150) -> str:
    """Получить предпросмотр текста."""
    if not text or not text.strip():
        return "(empty)"
    
    words = text.split()
    if len(words) <= max_words:
        return text.strip()[:800]
    
    preview = ' '.join(words[:max_words])
    return preview[:800] + "..."


class DOCXParser:
    """Универсальный парсер документов на базе pandoc.
    
    Поддерживает:
    - Word: .doc, .docx (pandoc + python-docx fallback)
    - PDF: .pdf
    - OpenDocument: .odt
    - RTF: .rtf
    - и 150+ других форматов
    """
    
    def __init__(self) -> None:
        self.text_cleaner = TextCleaner()
        self._pandoc_available = self._check_pandoc()
    
    @staticmethod
    def _check_pandoc() -> bool:
        """Check if pandoc is installed."""
        try:
            subprocess.run(
                ["pandoc", "--version"],
                capture_output=True,
                timeout=5
            )
            logger.info("✓ pandoc is installed and available")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠ pandoc is NOT installed. Install it first!")
            logger.warning("Windows: choco install pandoc")
            logger.warning("Linux: apt-get install pandoc")
            logger.warning("macOS: brew install pandoc")
            return False
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from document using pandoc.
        
        Args:
            file_path: Path to document file
            
        Returns:
            str: Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If pandoc is not installed or extraction fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self._pandoc_available:
            raise ValueError(
                "pandoc is not installed. "
                "Install it: Windows (choco install pandoc), "
                "Linux (apt-get install pandoc), "
                "macOS (brew install pandoc)"
            )
        
        logger.info(f"Starting extraction from {file_path.name} ({file_path.stat().st_size} bytes)")
        
        suffix = file_path.suffix.lower()
        
        # Try pandoc first (works with almost everything)
        logger.info(f"Trying pandoc for {suffix} format")
        result = self._extract_with_pandoc(file_path)
        
        if result and result.strip():
            logger.info(f"✓ Pandoc extraction successful: {len(result)} chars")
            preview = _get_text_preview(result, max_words=150)
            logger.info(f"📝 TEXT PREVIEW:\n{preview}")
            return result
        
        # Fallback: try python-docx for DOCX files
        if suffix == '.docx' and DocxDocument:
            logger.info(f"Fallback: Trying python-docx for DOCX")
            result = self._extract_with_python_docx(file_path)
            
            if result and result.strip():
                logger.info(f"✓ python-docx extraction successful: {len(result)} chars")
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW:\n{preview}")
                return result
        
        raise ValueError(f"Cannot extract text from {file_path.name}")
    
    def _extract_with_pandoc(self, file_path: Path) -> str:
        """Extract text using pandoc converter.
        
        Converts document to plain text using pandoc.
        Works with: .doc, .docx, .pdf, .odt, .rtf, and 150+ other formats.
        """
        try:
            logger.debug(f"Using pandoc for {file_path.name}")
            
            # pandoc: input_file -t plain -o output_file
            # We use -t plain for plain text output
            result = subprocess.run(
                ["pandoc", str(file_path), "-t", "plain"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                text = result.stdout.strip()
                if text:
                    logger.debug(f"pandoc returned {len(text)} chars")
                    return text
                else:
                    logger.debug(f"pandoc returned empty text")
                    return ""
            else:
                logger.warning(f"pandoc failed with return code {result.returncode}")
                if result.stderr:
                    logger.warning(f"pandoc error: {result.stderr[:100]}")
                return ""
        
        except subprocess.TimeoutExpired:
            logger.error(f"pandoc conversion timed out for {file_path.name}")
            return ""
        except Exception as e:
            logger.error(f"pandoc extraction error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def _extract_with_python_docx(self, file_path: Path) -> str:
        """Extract text from .docx files using python-docx (fallback)."""
        if DocxDocument is None:
            logger.debug("python-docx not installed")
            return ""
        
        try:
            logger.debug(f"Using python-docx for {file_path.name}")
            doc = DocxDocument(file_path)
            
            extracted = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    extracted.append(para.text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            if para.text.strip():
                                row_text.append(para.text)
                    if row_text:
                        extracted.append(" | ".join(row_text))
            
            return "\n".join(extracted)
        
        except Exception as e:
            logger.error(f"python-docx error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def get_metadata(self, file_path: Path) -> dict:  # type: ignore
        """Extract document metadata (DOCX only)."""
        try:
            if file_path.suffix.lower() != '.docx':
                return {}
            
            doc = DocxDocument(file_path)
            props = doc.core_properties
            return {
                "title": props.title,
                "author": props.author,
                "subject": props.subject,
                "created": props.created,
                "modified": props.modified,
            }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {}
