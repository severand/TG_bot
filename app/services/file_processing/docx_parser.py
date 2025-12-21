"""Document parser using proven libraries.

ОКОНЧАТЕЛЬНОЕ РЕШЕНИЕ 2025-12-21 13:15:
- НИКАКих экспериментов, только WORKING LIBRARIES
- python-docx ✅ работает с .docx и .doc
- pypdf ✅ работает с PDF
- python-pptx ✅ работает с PowerPoint
- openpyxl ✅ работает с Excel
"""

import logging
from pathlib import Path
from typing import Optional

from app.services.file_processing.text_cleaner import TextCleaner

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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
    """Парсер для всех документов.
    
    Поддерживает:
    - Word: .doc, .docx (python-docx)
    - PDF: .pdf (pypdf)
    - PowerPoint: .ppt, .pptx (python-pptx)
    - Excel: .xls, .xlsx (openpyxl)
    """
    
    def __init__(self) -> None:
        self.text_cleaner = TextCleaner()
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from document.
        
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
        
        suffix = file_path.suffix.lower()
        
        # Route to appropriate extractor based on file type
        if suffix in ['.doc', '.docx']:
            logger.info(f"Detected Word document: {suffix}")
            result = self._extract_word(file_path)
        elif suffix == '.pdf':
            logger.info(f"Detected PDF document")
            result = self._extract_pdf(file_path)
        elif suffix in ['.ppt', '.pptx']:
            logger.info(f"Detected PowerPoint document: {suffix}")
            result = self._extract_pptx(file_path)
        elif suffix in ['.xls', '.xlsx']:
            logger.info(f"Detected Excel document: {suffix}")
            result = self._extract_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        if result and result.strip():
            logger.info(f"✓ Extraction successful: {len(result)} chars")
            preview = _get_text_preview(result, max_words=150)
            logger.info(f"📝 TEXT PREVIEW:\n{preview}")
            return result
        else:
            raise ValueError(f"No text extracted from {file_path.name}")
    
    def _extract_word(self, file_path: Path) -> str:
        """Extract text from .doc or .docx files using python-docx.
        
        Works with BOTH old .doc and new .docx formats.
        """
        if DocxDocument is None:
            logger.error("python-docx not installed")
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
            logger.error(f"Word extraction error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF files using pypdf."""
        if PdfReader is None:
            logger.error("pypdf not installed")
            return ""
        
        try:
            logger.debug(f"Using pypdf for {file_path.name}")
            reader = PdfReader(file_path)
            
            extracted = []
            for page in reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    extracted.append(text)
            
            return "\n\n".join(extracted)
        
        except Exception as e:
            logger.error(f"PDF extraction error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def _extract_pptx(self, file_path: Path) -> str:
        """Extract text from PowerPoint files (.ppt, .pptx) using python-pptx."""
        if Presentation is None:
            logger.error("python-pptx not installed")
            return ""
        
        try:
            logger.debug(f"Using python-pptx for {file_path.name}")
            prs = Presentation(file_path)
            
            extracted = []
            for slide_idx, slide in enumerate(prs.slides, 1):
                slide_text = []
                
                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)
                
                if slide_text:
                    extracted.append(f"--- Slide {slide_idx} ---")
                    extracted.extend(slide_text)
            
            return "\n".join(extracted)
        
        except Exception as e:
            logger.error(f"PowerPoint extraction error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def _extract_excel(self, file_path: Path) -> str:
        """Extract text from Excel files (.xls, .xlsx) using openpyxl."""
        if load_workbook is None:
            logger.error("openpyxl not installed")
            return ""
        
        try:
            logger.debug(f"Using openpyxl for {file_path.name}")
            wb = load_workbook(file_path)
            
            extracted = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                
                extracted.append(f"=== Sheet: {sheet_name} ===")
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = [str(cell) if cell is not None else "" for cell in row]
                    if any(row_text):
                        extracted.append(" | ".join(row_text))
            
            return "\n".join(extracted)
        
        except Exception as e:
            logger.error(f"Excel extraction error: {type(e).__name__}: {str(e)[:100]}")
            return ""
    
    def get_metadata(self, file_path: Path) -> dict:  # type: ignore
        """Extract document metadata."""
        try:
            if file_path.suffix.lower() not in ['.docx', '.doc']:
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
