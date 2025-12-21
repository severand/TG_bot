"""DOCX file parser with robust error handling for old .doc files.

КРИТИЧЕСКОЕ ОБНОВЛЕНИЕ 2025-12-21 13:10:
- НОВОЕ: Корректный пакет docx2txt (без python-)
- Метод _extract_using_docx2txt() использует docx2txt.convert()
- КОРРЕКТНОЕ решение для .doc файлов

Handles extraction of text content from Microsoft Word (.docx) files
using python-docx library with graceful fallback for corrupted files.
"""

import logging
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree as ET
from typing import Optional
import re

from app.services.file_processing.text_cleaner import TextCleaner

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

try:
    import docx2txt
except ImportError:
    docx2txt = None

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
    """Парсер для DOCX и старых .doc файлов.
    
    Порядок исвлечения:
    1. python-docx (.docx файлы)
    2. docx2txt (.doc файлы) ✅ ПРАВИЛЬНЫЙ МЕТОД!
    3. ZIP extraction (поврежденные .docx)
    4. Binary extraction (последняя попытка)
    """
    
    def __init__(self) -> None:
        """Инициализация парсера."""
        self.text_cleaner = TextCleaner()
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from DOCX file.
        
        Extracts text from paragraphs and tables, preserving document structure.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text with structure preserved
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid DOCX
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
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW (first 150 words):\n{preview}")
                return result
            else:
                logger.warning(f"python-docx returned empty text, trying fallback")
        
        except Exception as e:
            logger.warning(
                f"python-docx failed for {file_path.name}: "
                f"{type(e).__name__}: {str(e)[:100]}"
            )
            logger.info(f"This might be an old .doc file, trying docx2txt...")
        
        # Fallback 1: Use docx2txt for .doc files (CORRECT METHOD!)
        logger.info(f"Step 1: Trying docx2txt for {file_path.name}")
        try:
            result = self._extract_using_docx2txt(file_path)
            if result and result.strip():
                logger.info(f"✓ docx2txt extraction successful: {len(result)} chars")
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW (docx2txt):\n{preview}")
                return result
            else:
                logger.info(f"docx2txt returned empty result, continuing to ZIP method...")
        except Exception as e:
            logger.warning(f"docx2txt failed with {type(e).__name__}: {str(e)[:100]}")
            logger.info(f"Continuing to ZIP method...")
        
        # Fallback 2: Extract directly from ZIP (for corrupted DOCX files)
        logger.info(f"Step 2: Trying ZIP extraction for {file_path.name}")
        try:
            result = self._extract_from_zip(file_path)
            if result and result.strip():
                logger.info(f"✓ ZIP extraction successful: {len(result)} chars")
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW (ZIP):\n{preview}")
                return result
            else:
                logger.info(f"ZIP extraction returned empty result, continuing to binary method...")
        
        except BadZipFile:
            logger.info(f"File is not a ZIP archive, continuing to binary method...")
        except Exception as e:
            logger.warning(f"ZIP fallback failed with {type(e).__name__}, continuing to binary...")
        
        # Fallback 3: Extract from binary (last resort)
        logger.info(f"Step 3: Trying binary extraction for {file_path.name}")
        try:
            result = self._extract_from_binary_doc(file_path)
            if result and result.strip():
                logger.info(f"✓ Binary extraction successful: {len(result)} chars")
                preview = _get_text_preview(result, max_words=150)
                logger.info(f"📝 TEXT PREVIEW (Binary):\n{preview}")
                return result
            else:
                logger.warning(f"Binary extraction returned empty result")
                return ""
        
        except Exception as e:
            logger.error(f"Binary extraction failed: {type(e).__name__}: {e}")
            raise ValueError(f"Invalid DOCX/DOC file: Cannot extract text using any method") from e
    
    def _extract_using_docx2txt(self, file_path: Path) -> str:
        """Extract text using docx2txt (proper .doc extraction).
        
        This is the CORRECT way to extract text from MS Word 97-2003 .doc files.
        Uses the official docx2txt library.
        
        Args:
            file_path: Path to .doc or .docx file
            
        Returns:
            str: Extracted text
        """
        if docx2txt is None:
            logger.debug("docx2txt library not installed - skipping")
            return ""
        
        try:
            logger.debug(f"Using docx2txt.convert() for {file_path.name}")
            text = docx2txt.convert(str(file_path))
            
            if text and text.strip():
                logger.debug(f"docx2txt returned {len(text)} chars")
                return text
            else:
                logger.debug(f"docx2txt returned empty text")
                return ""
        
        except Exception as e:
            logger.debug(f"docx2txt extraction error: {type(e).__name__}: {str(e)[:50]}")
            return ""
    
    def _extract_from_zip(self, file_path: Path) -> str:
        """Extract text directly from DOCX ZIP archive.
        
        DOCX is a ZIP file containing document.xml which has the text.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text from XML
        """
        logger.debug(f"ZIP extraction: checking if file is ZIP archive")
        
        all_text = []
        
        try:
            with ZipFile(file_path, 'r') as docx_zip:
                file_list = docx_zip.namelist()
                logger.debug(f"ZIP contains {len(file_list)} files")
                
                # Try document.xml first (main content)
                if 'word/document.xml' in file_list:
                    try:
                        text = self._extract_text_from_xml(docx_zip, 'word/document.xml')
                        if text and text.strip():
                            all_text.append(text)
                            logger.debug(f"ZIP: extracted {len(text)} chars from document.xml")
                    except Exception as e:
                        logger.debug(f"ZIP: failed to parse document.xml: {type(e).__name__}")
                
                # Try other XML files as fallback
                for file_name in file_list:
                    if file_name.endswith('.xml') and 'word/' in file_name and file_name != 'word/document.xml':
                        try:
                            text = self._extract_text_from_xml(docx_zip, file_name)
                            if text and text.strip():
                                all_text.append(text)
                                logger.debug(f"ZIP: extracted {len(text)} chars from {file_name}")
                        except Exception:
                            continue
        
        except BadZipFile:
            logger.debug(f"ZIP: file is not a valid ZIP archive")
            return ""
        except Exception as e:
            logger.debug(f"ZIP extraction error: {type(e).__name__}: {str(e)[:50]}")
            return ""
        
        result = "\n\n".join(all_text)
        logger.debug(f"ZIP extraction result: {len(result)} chars total")
        return result
    
    def _extract_text_from_xml(self, docx_zip: ZipFile, xml_path: str) -> str:
        """Extract text from XML file in DOCX ZIP.
        
        Args:
            docx_zip: ZipFile object
            xml_path: Path to XML file in ZIP
            
        Returns:
            str: Extracted text
        """
        try:
            xml_content = docx_zip.read(xml_path).decode('utf-8', errors='ignore')
            
            if not xml_content.strip():
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
                return text
            
            except ET.ParseError:
                return self._extract_plain_text_from_corrupted_xml(xml_content)
        
        except Exception:
            return ""
    
    def _extract_from_binary_doc(self, file_path: Path) -> str:
        """Try to extract text from binary .doc format.
        
        This is a last resort when all other methods fail.
        
        Args:
            file_path: Path to .doc file
            
        Returns:
            str: Extracted text
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            if not content:
                logger.warning(f"File {file_path.name} is empty")
                return ""
            
            # Strategy 1: Look for continuous printable strings
            text_parts = self._extract_continuous_strings(content)
            if text_parts:
                text = ' '.join(text_parts)
                if len(text) > 50:
                    logger.debug(f"Binary: found {len(text)} chars using continuous string method")
                    return text.strip()
            
            # Strategy 2: Look for UTF-16 encoded text
            try:
                text = self._extract_utf16_strings(content)
                if text and len(text.strip()) > 50:
                    logger.debug(f"Binary: found {len(text)} chars using UTF-16 method")
                    return text.strip()
            except:
                pass
            
            logger.debug(f"Binary: no substantial text found")
            return ""
        
        except Exception as e:
            logger.error(f"Binary extraction failed: {type(e).__name__}: {e}")
            return ""
    
    def _extract_continuous_strings(self, content: bytes, min_len: int = 4) -> list[str]:
        """Extract continuous printable strings from binary data.
        
        Args:
            content: Binary content
            min_len: Minimum string length to consider
            
        Returns:
            List of strings found
        """
        strings = []
        current = b''
        
        for byte in content:
            if 32 <= byte <= 126:  # Printable ASCII
                current += bytes([byte])
            else:
                if len(current) >= min_len:
                    try:
                        s = current.decode('ascii', errors='ignore').strip()
                        if s:
                            strings.append(s)
                    except:
                        pass
                current = b''
        
        # Don't forget the last one
        if len(current) >= min_len:
            try:
                s = current.decode('ascii', errors='ignore').strip()
                if s:
                    strings.append(s)
            except:
                pass
        
        return strings
    
    def _extract_utf16_strings(self, content: bytes) -> str:
        """Extract UTF-16 encoded strings.
        
        Args:
            content: Binary content
            
        Returns:
            Extracted text
        """
        # Try UTF-16 LE (little-endian, common in Windows)
        try:
            decoded = content.decode('utf-16-le', errors='ignore')
            words = re.findall(r'[\w\s]{2,}', decoded)
            if words:
                return ' '.join(words).strip()
        except:
            pass
        
        # Try UTF-16 BE (big-endian)
        try:
            decoded = content.decode('utf-16-be', errors='ignore')
            words = re.findall(r'[\w\s]{2,}', decoded)
            if words:
                return ' '.join(words).strip()
        except:
            pass
        
        return ""
    
    @staticmethod
    def _extract_plain_text_from_corrupted_xml(xml_content: str) -> str:
        """Extract readable text from corrupted XML.
        
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
