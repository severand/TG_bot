"""PDF file parser module for RAG.

Handles extraction of text content from PDF files using pypdf.
Includes error handling for corrupted or malformed PDFs.
"""

import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFParser:
    """Parser for PDF documents.
    
    Attributes:
        max_pages: Maximum pages to extract (None = all pages)
    """
    
    def __init__(self, max_pages: Optional[int] = None) -> None:
        """Initialize PDF parser.
        
        Args:
            max_pages: Limit extraction to first N pages.
        """
        self.max_pages = max_pages
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from PDF file.
        
        Iterates through all pages (or limited by max_pages) and
        extracts text content. Skips pages where text extraction fails.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text with page separators
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
        """
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        try:
            reader = PdfReader(file_path)
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            raise ValueError(f"Invalid PDF file: {e}") from e
        
        if not reader.pages:
            logger.warning(f"PDF {file_path} has no pages")
            return ""
        
        extracted_text: list[str] = []
        pages_to_process = min(len(reader.pages), self.max_pages or len(reader.pages))        
        for page_num in range(pages_to_process):
            try:
                page = reader.pages[page_num]
                text = page.extract_text()
                if text and text.strip():
                    extracted_text.append(f"--- Page {page_num + 1} ---\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                continue
        
        result = "\n\n".join(extracted_text)
        logger.info(f"Extracted {len(extracted_text)} pages from {file_path.name}")
        return result
    
    def get_metadata(self, file_path: Path) -> dict:
        """Extract PDF metadata.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            dict: PDF metadata (title, author, creation_date, etc.)
        """
        try:
            reader = PdfReader(file_path)
            return reader.metadata or {}
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            return {}
