"""DOCX file parser module.

Handles extraction of text content from Microsoft Word (.docx) files
using python-docx library.
"""

import logging
from pathlib import Path
from typing import Optional

from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import _Cell

logger = logging.getLogger(__name__)


class DOCXParser:
    """Parser for DOCX (Microsoft Word) documents."""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from DOCX file.
        
        Extracts text from paragraphs and tables, preserving document structure.
        Handles corrupted files gracefully.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text with structure preserved
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid DOCX
            
        Example:
            >>> parser = DOCXParser()
            >>> text = parser.extract_text(Path("document.docx"))
        """
        if not file_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")
        
        try:
            doc = Document(file_path)
        except Exception as e:
            logger.error(f"Failed to read DOCX {file_path}: {e}")
            raise ValueError(f"Invalid DOCX file: {e}") from e
        
        extracted_text: list[str] = []
        
        # Extract paragraphs
        for paragraph in doc.paragraphs:
            text = self._extract_paragraph_text(paragraph)
            if text:
                extracted_text.append(text)
        
        # Extract tables
        for table in doc.tables:
            table_text = self._extract_table_text(table)
            if table_text:
                extracted_text.append(table_text)
        
        result = "\n".join(extracted_text)
        logger.info(f"Extracted text from {file_path.name}")
        return result
    
    def _extract_paragraph_text(self, paragraph: Paragraph) -> str:
        """Extract text from a paragraph with formatting preserved.
        
        Args:
            paragraph: Paragraph object
            
        Returns:
            str: Paragraph text
        """
        # Handle heading styles
        text = paragraph.text
        if not text.strip():
            return ""
        
        # Preserve heading formatting with markdown
        if paragraph.style.name.startswith("Heading"):
            level = int(paragraph.style.name.replace("Heading", ""))
            return f"{'#' * level} {text}"
        
        return text
    
    def _extract_table_text(self, table) -> str:  # type: ignore
        """Extract text from a table.
        
        Args:
            table: Table object
            
        Returns:
            str: Formatted table text
        """
        rows: list[list[str]] = []
        
        for row in table.rows:
            cells: list[str] = []
            for cell in row.cells:
                cell_text = self._extract_cell_text(cell)
                cells.append(cell_text)
            rows.append(cells)
        
        if not rows:
            return ""
        
        # Format as markdown table
        table_text = []
        
        # Header
        table_text.append(" | ".join(rows[0]))
        table_text.append(" | ".join(["---"] * len(rows[0])))
        
        # Body
        for row in rows[1:]:
            table_text.append(" | ".join(row))
        
        return "\n" + "\n".join(table_text) + "\n"
    
    def _extract_cell_text(self, cell: _Cell) -> str:  # type: ignore
        """Extract text from a table cell.
        
        Args:
            cell: Table cell object
            
        Returns:
            str: Cell text
        """
        cell_text = []
        for paragraph in cell.paragraphs:
            text = paragraph.text.strip()
            if text:
                cell_text.append(text)
        return " ".join(cell_text)
    
    def get_metadata(self, file_path: Path) -> dict:
        """Extract DOCX metadata.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            dict: Document metadata (author, title, creation_date, etc.)
        """
        try:
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
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            return {}
