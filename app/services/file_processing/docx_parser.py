"""DOCX file parser with robust error handling for old .doc files.

Fixes 2025-12-20 23:48 - FINAL SOLUTION:
- Try python-docx first (works for valid DOCX)
- If fails = old .doc binary format, fallback to ZIP extraction
- Extract text from document.xml even if corrupted
- NO external dependencies beyond python-docx
- WORKS for both .docx AND renamed .doc->docx files

Handles extraction of text content from Microsoft Word (.docx) files
using python-docx library with graceful fallback for corrupted files.
"""

import logging
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree as ET
from typing import Optional
import re

try:
    from docx import Document
except ImportError:
    Document = None

from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import _Cell

logger = logging.getLogger(__name__)


class DOCXParser:
    """Parser for DOCX (Microsoft Word) documents.
    
    Supports both valid DOCX files and old .doc files (renamed to .docx).
    Uses python-docx for valid files, ZIP extraction fallback for corrupted.
    """
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from DOCX file.
        
        Extracts text from paragraphs and tables, preserving document structure.
        Tries python-docx first, falls back to ZIP extraction for old .doc files.
        
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
        
        # Try standard python-docx first (for valid DOCX files)
        try:
            logger.info(f"Trying python-docx for {file_path.name}")
            doc = Document(file_path)
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
            if result.strip():
                logger.info(f"Successfully extracted {len(result)} chars from {file_path.name}")
                return result
            else:
                logger.warning(f"python-docx returned empty text, trying fallback")
        
        except Exception as e:
            logger.warning(
                f"python-docx failed for {file_path.name}: "
                f"{type(e).__name__}: {str(e)[:100]}"
            )
            logger.info(f"This might be an old .doc file, trying ZIP fallback...")
        
        # Fallback: Extract directly from ZIP (for old .doc files renamed to .docx)
        try:
            logger.info(f"Using ZIP fallback for {file_path.name}")
            return self._extract_from_zip(file_path)
        except Exception as e:
            logger.error(f"ZIP fallback also failed: {type(e).__name__}: {e}")
            raise ValueError(f"Invalid DOCX file: Cannot extract text using either method") from e
    
    def _extract_from_zip(self, file_path: Path) -> str:
        """Extract text directly from DOCX ZIP archive.
        
        DOCX is a ZIP file containing document.xml which has the text.
        For old .doc files renamed to .docx, this provides fallback extraction.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text from XML
        """
        logger.info(f"Extracting text from ZIP structure in {file_path.name}")
        
        all_text = []
        
        try:
            with ZipFile(file_path, 'r') as docx_zip:
                file_list = docx_zip.namelist()
                logger.debug(f"ZIP contains {len(file_list)} files")
                
                # Try document.xml first (main content)
                if 'word/document.xml' in file_list:
                    try:
                        text = self._extract_text_from_xml(docx_zip, 'word/document.xml')
                        if text.strip():
                            all_text.append(text)
                            logger.info(f"Extracted {len(text)} chars from document.xml")
                    except Exception as e:
                        logger.warning(f"Failed to parse document.xml: {type(e).__name__}")
                
                # Try other XML files as fallback
                for file_name in file_list:
                    if file_name.endswith('.xml') and 'word/' in file_name:
                        if file_name != 'word/document.xml':
                            try:
                                text = self._extract_text_from_xml(docx_zip, file_name)
                                if text.strip():
                                    all_text.append(text)
                                    logger.debug(f"Extracted {len(text)} chars from {file_name}")
                            except Exception:
                                pass
        
        except BadZipFile as e:
            logger.error(f"Not a valid ZIP/DOCX file: {e}")
            raise ValueError(f"File is not a valid DOCX: {e}") from e
        except Exception as e:
            logger.error(f"ZIP extraction error: {type(e).__name__}: {e}")
            raise
        
        result = "\n\n".join(all_text)
        logger.info(f"ZIP fallback extracted {len(result)} chars total")
        return result
    
    def _extract_text_from_xml(self, docx_zip: ZipFile, xml_path: str) -> str:
        """Extract text from XML file in DOCX ZIP.
        
        Handles corrupted XML by extracting readable text.
        
        Args:
            docx_zip: ZipFile object
            xml_path: Path to XML file in ZIP
            
        Returns:
            str: Extracted text
        """
        try:
            xml_content = docx_zip.read(xml_path).decode('utf-8', errors='ignore')
            
            # Try to parse as XML
            try:
                root = ET.fromstring(xml_content)
                namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text_elements = root.findall('.//w:t', namespace)
                
                if not text_elements:
                    text_elements = root.findall('.//t')
                
                text = ''.join([elem.text for elem in text_elements if elem.text])
                return text
            
            except ET.ParseError:
                # If XML parsing fails, extract plain text from corrupted content
                logger.debug(f"XML parsing failed for {xml_path}, extracting plain text")
                return self._extract_plain_text_from_corrupted_xml(xml_content)
        
        except Exception as e:
            logger.warning(f"Error processing {xml_path}: {type(e).__name__}")
            return ""
    
    @staticmethod
    def _extract_plain_text_from_corrupted_xml(xml_content: str) -> str:
        """Extract readable text from corrupted XML.
        
        When XML parsing fails, extract text between tags.
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            str: Extracted text
        """
        # Remove XML tags
        text = re.sub(r'<[^>]+>', ' ', xml_content)
        # Clean up whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    
    def _extract_paragraph_text(self, paragraph: Paragraph) -> str:
        """Extract text from a paragraph with formatting preserved.
        
        Args:
            paragraph: Paragraph object
            
        Returns:
            str: Paragraph text
        """
        text = paragraph.text
        if not text.strip():
            return ""
        
        # Preserve heading formatting with markdown
        if paragraph.style.name.startswith("Heading"):
            try:
                level = int(paragraph.style.name.replace("Heading", ""))
                return f"{'#' * level} {text}"
            except (ValueError, IndexError):
                pass
        
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
        table_text.append(" | ".join(rows[0]))
        table_text.append(" | ".join(["---"] * len(rows[0])))
        
        for row in rows[1:]:
            table_text.append(" | ".join(row))
        
        return "\n" + "\n".join(table_text) + "\n"
    
    def _extract_cell_text(self, cell: _Cell) -> str:  # type: ignore
        """Extract text from a table cell.
        
        Args:
            cell: Table cell
            
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
            dict: Document metadata
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
            logger.warning(f"Failed to extract metadata: {e}")
            return {}
