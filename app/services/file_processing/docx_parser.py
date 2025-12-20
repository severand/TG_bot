"""DOCX file parser with robust error handling for old .doc files.

Fixes 2025-12-20 23:55 - IMPROVED SOLUTION:
- Try python-docx first (works for valid DOCX)
- If fails = old .doc binary format, fallback to ZIP extraction
- Extract text from document.xml even if corrupted
- Handle cases where ZIP structure is incomplete
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

try:
    from docx.oxml.text.paragraph import CT_P
    from docx.text.paragraph import Paragraph
    from docx.table import _Cell
except ImportError:
    CT_P = None
    Paragraph = None
    _Cell = None

logger = logging.getLogger(__name__)


class DOCXParser:
    """Parser for DOCX (Microsoft Word) documents.
    
    Supports both valid DOCX files and old .doc files (renamed to .docx).
    Uses python-docx for valid files, ZIP extraction fallback for corrupted.
    Handles incomplete ZIP structures and corrupted XML gracefully.
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
        
        logger.info(f"Starting extraction from {file_path.name} ({file_path.stat().st_size} bytes)")
        
        # Try standard python-docx first (for valid DOCX files)
        try:
            logger.info(f"Trying python-docx for {file_path.name}")
            doc = Document(file_path)
            extracted_text: list[str] = []
            
            # Extract paragraphs
            paragraph_count = 0
            for paragraph in doc.paragraphs:
                text = self._extract_paragraph_text(paragraph)
                if text:
                    extracted_text.append(text)
                    paragraph_count += 1
            
            logger.debug(f"Extracted {paragraph_count} paragraphs")
            
            # Extract tables
            table_count = 0
            for table in doc.tables:
                table_text = self._extract_table_text(table)
                if table_text:
                    extracted_text.append(table_text)
                    table_count += 1
            
            logger.debug(f"Extracted {table_count} tables")
            
            result = "\n".join(extracted_text)
            if result.strip():
                logger.info(f"✓ Successfully extracted {len(result)} chars from {file_path.name} "
                          f"({paragraph_count} paragraphs, {table_count} tables)")
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
            result = self._extract_from_zip(file_path)
            if result.strip():
                logger.info(f"✓ ZIP fallback extracted {len(result)} chars")
                return result
            else:
                logger.warning(f"ZIP fallback extracted 0 chars, file might be empty or corrupted")
                # Return empty string instead of raising, to show user file was processed
                return ""
        
        except Exception as e:
            logger.error(f"ZIP fallback also failed: {type(e).__name__}: {e}")
            raise ValueError(f"Invalid DOCX file: Cannot extract text using either method") from e
    
    def _extract_from_zip(self, file_path: Path) -> str:
        """Extract text directly from DOCX ZIP archive.
        
        DOCX is a ZIP file containing document.xml which has the text.
        For old .doc files renamed to .docx, this provides fallback extraction.
        Also handles incomplete or corrupted ZIP structures.
        
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
                logger.debug(f"ZIP contains {len(file_list)} files: {', '.join(file_list[:5])}...")
                
                # Try document.xml first (main content)
                if 'word/document.xml' in file_list:
                    try:
                        text = self._extract_text_from_xml(docx_zip, 'word/document.xml')
                        if text.strip():
                            all_text.append(text)
                            logger.info(f"Extracted {len(text)} chars from document.xml")
                        else:
                            logger.debug("document.xml exists but is empty or has no text elements")
                    except Exception as e:
                        logger.warning(f"Failed to parse document.xml: {type(e).__name__}: {e}")
                
                # Try other XML files as fallback (headers, footers, comments)
                xml_files_tried = 0
                for file_name in file_list:
                    if file_name.endswith('.xml') and 'word/' in file_name:
                        if file_name != 'word/document.xml':
                            try:
                                text = self._extract_text_from_xml(docx_zip, file_name)
                                if text.strip():
                                    all_text.append(text)
                                    xml_files_tried += 1
                                    logger.debug(f"Extracted {len(text)} chars from {file_name}")
                            except Exception as e:
                                logger.debug(f"Failed to process {file_name}: {type(e).__name__}")
                
                if xml_files_tried > 0:
                    logger.info(f"Extracted text from {xml_files_tried} additional XML files")
        
        except BadZipFile as e:
            logger.error(f"Not a valid ZIP/DOCX file: {e}")
            # Try to handle as old .doc binary format
            logger.info(f"File might be old .doc binary format, attempting binary extraction")
            try:
                text = self._extract_from_binary_doc(file_path)
                if text.strip():
                    return text
            except Exception as be:
                logger.debug(f"Binary extraction failed: {be}")
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
            
            if not xml_content.strip():
                logger.debug(f"{xml_path} is empty")
                return ""
            
            # Try to parse as XML
            try:
                root = ET.fromstring(xml_content)
                namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text_elements = root.findall('.//w:t', namespace)
                
                # Fallback: try without namespace
                if not text_elements:
                    text_elements = root.findall('.//t')
                
                text_parts = []
                for elem in text_elements:
                    if elem.text:
                        text_parts.append(elem.text)
                
                text = ''.join(text_parts)
                logger.debug(f"XML parsing found {len(text_elements)} text elements")
                return text
            
            except ET.ParseError as pe:
                # If XML parsing fails, extract plain text from corrupted content
                logger.debug(f"XML parsing failed for {xml_path} ({pe}), extracting plain text")
                return self._extract_plain_text_from_corrupted_xml(xml_content)
        
        except Exception as e:
            logger.warning(f"Error processing {xml_path}: {type(e).__name__}: {e}")
            return ""
    
    def _extract_from_binary_doc(self, file_path: Path) -> str:
        """Try to extract text from binary .doc format.
        
        Old MS Word .doc files are binary, not ZIP.
        This attempts to extract readable ASCII/UTF-8 strings.
        
        Args:
            file_path: Path to .doc file
            
        Returns:
            str: Extracted text
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Look for null-separated strings (Word structure)
            text_parts = []
            current_word = b''
            
            for byte in content:
                if 32 <= byte <= 126 or byte in (9, 10, 13):  # ASCII printable + whitespace
                    current_word += bytes([byte])
                else:
                    if len(current_word) > 3:  # Only keep words > 3 chars
                        try:
                            text_parts.append(current_word.decode('utf-8', errors='ignore'))
                        except:
                            pass
                    current_word = b''
            
            text = ' '.join(text_parts)
            logger.info(f"Binary extraction found {len(text)} chars")
            return text
        
        except Exception as e:
            logger.error(f"Binary extraction failed: {e}")
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
        text = text.strip()
        return text
    
    def _extract_paragraph_text(self, paragraph) -> str:  # type: ignore
        """Extract text from a paragraph with formatting preserved.
        
        Args:
            paragraph: Paragraph object
            
        Returns:
            str: Paragraph text
        """
        try:
            text = paragraph.text
            if not text.strip():
                return ""
            
            # Preserve heading formatting with markdown
            if hasattr(paragraph, 'style') and paragraph.style.name.startswith("Heading"):
                try:
                    level = int(paragraph.style.name.replace("Heading", ""))
                    return f"{'#' * level} {text}"
                except (ValueError, IndexError):
                    pass
            
            return text
        except Exception as e:
            logger.debug(f"Error extracting paragraph text: {e}")
            return ""
    
    def _extract_table_text(self, table) -> str:  # type: ignore
        """Extract text from a table.
        
        Args:
            table: Table object
            
        Returns:
            str: Formatted table text
        """
        try:
            rows: list[list[str]] = []
            
            for row in table.rows:
                cells: list[str] = []
                for cell in row.cells:
                    cell_text = self._extract_cell_text(cell)
                    cells.append(cell_text)
                if cells:
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
        except Exception as e:
            logger.debug(f"Error extracting table text: {e}")
            return ""
    
    def _extract_cell_text(self, cell) -> str:  # type: ignore
        """Extract text from a table cell.
        
        Args:
            cell: Table cell
            
        Returns:
            str: Cell text
        """
        try:
            cell_text = []
            for paragraph in cell.paragraphs:
                text = paragraph.text.strip()
                if text:
                    cell_text.append(text)
            return " ".join(cell_text)
        except Exception as e:
            logger.debug(f"Error extracting cell text: {e}")
            return ""
    
    def get_metadata(self, file_path: Path) -> dict:  # type: ignore
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
