"""DOCX file parser with robust error handling for all document types.

ОКОНЧАТЕЛЬНОЕ РЕШЕНИЕ 2025-12-21 13:13:
- Устанавливаем textract - универсальный парсер
- НУЖНУ textract.process(file_path)
- Все - .doc, .docx, .pdf, .xls, .txt, .rtf и т.д.

No more OLE hacks, no more FIB parsing, no more binary gymnastics.
Just simple, reliable text extraction using textract library.
"""

import logging
from pathlib import Path
from typing import Optional

from app.services.file_processing.text_cleaner import TextCleaner

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import textract
except ImportError:
    textract = None

logger = logging.getLogger(__name__)


def _get_text_preview(text: str, max_words: int = 150) -> str:
    """Получить предпросмотр текста (первые N слов).
    
    Args:
        text: Исходный текст
        max_words: Максимальное количество слов
        
    Returns:
        Предпросмотр текста
    """
    if not text or not text.strip():
        return "(empty)"
    
    # Разбиваем на слова
    words = text.split()
    
    if len(words) <= max_words:
        return text.strip()[:800]
    
    # Берем первые max_words слов
    preview = ' '.join(words[:max_words])
    return preview[:800] + "..."


class DOCXParser:
    """Парсер для всех типов документов.
    
    ОКОНЧАТЕЛЬНОЕ решение - теперь используем textract
    
    Поддерживает:
    - .docx (модерн Word)
    - .doc (старый Word 97-2003)
    - .pdf 
    - .xls, .xlsx
    - .ppt, .pptx
    - .txt, .rtf
    - и многое другое
    """
    
    def __init__(self) -> None:
        """Инициализация парсера."""
        self.text_cleaner = TextCleaner()
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from any document file.
        
        Uses textract library which supports:
        - MS Word (.doc, .docx)
        - PDF
        - Excel (.xls, .xlsx)
        - PowerPoint (.ppt, .pptx)
        - Text (.txt, .rtf)
        - And many more...
        
        Args:
            file_path: Path to document file
            
        Returns:
            str: Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be extracted
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Starting extraction from {file_path.name} ({file_path.stat().st_size} bytes)")
        
        # Try using textract first (works for almost everything)
        logger.info(f"Trying textract for {file_path.name}")
        try:
            result = self._extract_using_textract(file_path)
            if result and result.strip():
                logger.info(f"✓ textract extraction successful: {len(result)} chars")
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW:\n{preview}")
                return result
            else:
                logger.warning(f"textract returned empty result")
        except Exception as e:
            logger.warning(f"textract failed: {type(e).__name__}: {str(e)[:100]}")
        
        # Fallback: try python-docx for DOCX files specifically
        if file_path.suffix.lower() == '.docx':
            logger.info(f"Fallback: Trying python-docx for DOCX")
            try:
                result = self._extract_using_python_docx(file_path)
                if result and result.strip():
                    logger.info(f"✓ python-docx extraction successful: {len(result)} chars")
                    preview = _get_text_preview(result, max_words=150)
                    logger.info(f"📝 TEXT PREVIEW:\n{preview}")
                    return result
            except Exception as e:
                logger.warning(f"python-docx fallback failed: {type(e).__name__}")
        
        # If nothing worked, raise error
        raise ValueError(f"Cannot extract text from {file_path.name}")
    
    def _extract_using_textract(self, file_path: Path) -> str:
        """Extract text using textract library.
        
        This is the FINAL SOLUTION - textract works with all document formats.
        
        Args:
            file_path: Path to document
            
        Returns:
            str: Extracted text
        """
        if textract is None:
            logger.debug("textract library not installed - skipping")
            return ""
        
        try:
            logger.debug(f"Using textract.process() for {file_path.name}")
            
            # textract.process returns bytes, need to decode
            result = textract.process(str(file_path))
            
            if isinstance(result, bytes):
                text = result.decode('utf-8', errors='ignore')
            else:
                text = result
            
            if text and text.strip():
                logger.debug(f"textract returned {len(text)} chars")
                return text
            else:
                logger.debug(f"textract returned empty text")
                return ""
        
        except Exception as e:
            logger.debug(f"textract extraction error: {type(e).__name__}: {str(e)[:50]}")
            return ""
    
    def _extract_using_python_docx(self, file_path: Path) -> str:
        """Extract text using python-docx (fallback for DOCX files).
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text
        """
        if Document is None:
            logger.debug("python-docx not available")
            return ""
        
        try:
            logger.debug(f"Using python-docx for {file_path.name}")
            doc = Document(file_path)
            extracted_text = []
            
            # Extract paragraphs
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    extracted_text.append(text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = ' '.join([p.text for p in cell.paragraphs if p.text.strip()])
                        row_text.append(cell_text)
                    if row_text:
                        extracted_text.append(' | '.join(row_text))
            
            result = "\n".join(extracted_text)
            if result and result.strip():
                logger.debug(f"python-docx returned {len(result)} chars")
                return result
            else:
                logger.debug(f"python-docx returned empty text")
                return ""
        
        except Exception as e:
            logger.debug(f"python-docx error: {type(e).__name__}")
            return ""
    
    def get_metadata(self, file_path: Path) -> dict:  # type: ignore
        """Extract document metadata.
        
        Args:
            file_path: Path to document file
            
        Returns:
            dict: Document metadata
        """
        try:
            if file_path.suffix.lower() != '.docx':
                return {}
            
            doc = Document(file_path)
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
