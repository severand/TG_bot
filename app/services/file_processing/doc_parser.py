"""Specialized parser for old MS Word .doc binary format.

Handles extraction of text from old Microsoft Word .doc files (pre-2007).
Old .doc files use OLE (Object Linking and Embedding) compound binary format,
not ZIP like modern .docx files.

This parser provides specialized extraction methods optimized for binary .doc format.
"""

import logging
import re
from pathlib import Path
from typing import Optional

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
        return text.strip()[:800]  # Максимум 800 символов
    
    # Берем первые max_words слов
    preview = ' '.join(words[:max_words])
    return preview[:800] + "..."


class DOCParser:
    """Specialized parser for old binary .doc format.
    
    Old MS Word .doc files (97-2003) use OLE compound file format.
    This is completely different from modern .docx (which is ZIP-based).
    
    Handles:
    - OLE format detection
    - Text extraction from binary Word format
    - Multiple fallback strategies
    - Corrupted file recovery
    """
    
    # OLE signature (first 8 bytes of OLE files)
    OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from old binary .doc file.
        
        Uses multiple extraction strategies:
        1. Look for 16-bit Unicode strings (modern Word format)
        2. Look for ASCII text blocks separated by null bytes
        3. Extract continuous printable strings
        4. Decode as Latin-1/UTF-8
        
        Args:
            file_path: Path to .doc file
            
        Returns:
            str: Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file can't be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path.name}: {e}")
            raise ValueError(f"Cannot read file: {e}") from e
        
        if not content:
            logger.warning(f"{file_path.name} is empty")
            return ""
        
        logger.info(f"Analyzing {file_path.name} ({len(content)} bytes)")
        
        # Detect if it's really OLE format
        is_ole = self._is_ole_file(content)
        logger.info(f"File format: {'OLE (old .doc)' if is_ole else 'Unknown binary format'}")
        
        # Try multiple extraction methods
        results = []
        
        # Method 1: Unicode strings (UTF-16 LE)
        text = self._extract_unicode_strings(content)
        if text and len(text.strip()) > 20:
            results.append(("Unicode (UTF-16 LE)", len(text), text))
            logger.debug(f"Unicode extraction found {len(text)} chars")
        
        # Method 2: Null-separated blocks
        text = self._extract_null_blocks(content)
        if text and len(text.strip()) > 20:
            results.append(("Null-blocks", len(text), text))
            logger.debug(f"Null-block extraction found {len(text)} chars")
        
        # Method 3: Continuous ASCII strings
        text = self._extract_ascii_strings(content)
        if text and len(text.strip()) > 20:
            results.append(("ASCII strings", len(text), text))
            logger.debug(f"ASCII extraction found {len(text)} chars")
        
        # Choose best result (by length)
        if results:
            results.sort(key=lambda x: x[1], reverse=True)
            best_method, best_len, best_text = results[0]
            logger.info(f"✓ Best extraction: {best_method} ({best_len} chars)")
            
            # НОВОЕ: Предпросмотр текста
            preview = _get_text_preview(best_text, max_words=150)
            logger.info(f"📝 TEXT PREVIEW ({best_method}, first 150 words):\n{preview}")
            
            return best_text.strip()
        
        logger.warning(f"No substantial text found in {file_path.name}")
        return ""
    
    def _is_ole_file(self, content: bytes) -> bool:
        """Check if file is OLE format (old .doc).
        
        Args:
            content: File binary content
            
        Returns:
            bool: True if OLE format
        """
        if len(content) >= 8:
            return content[:8] == self.OLE_SIGNATURE
        return False
    
    def _extract_unicode_strings(self, content: bytes) -> str:
        """Extract UTF-16 LE encoded strings.
        
        Modern MS Word stores text in UTF-16 LE encoding.
        Look for readable words in this format.
        
        Args:
            content: Binary content
            
        Returns:
            str: Extracted text
        """
        try:
            # Decode as UTF-16 LE with error tolerance
            decoded = content.decode('utf-16-le', errors='ignore')
            
            # Extract words (letters, digits, common punctuation)
            # Keep whitespace to preserve structure
            text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', decoded)  # Remove control chars
            text = re.sub(r' +', ' ', text)  # Collapse whitespace
            
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug(f"Unicode extraction failed: {e}")
        
        return ""
    
    def _extract_null_blocks(self, content: bytes) -> str:
        """Extract text from null-separated blocks.
        
        In binary .doc format, text often appears in blocks separated by null bytes.
        Each block contains readable characters between null bytes.
        
        Args:
            content: Binary content
            
        Returns:
            str: Extracted text
        """
        words = []
        current_word = b''
        
        for byte in content:
            # Printable ASCII + common extended ASCII
            if (32 <= byte <= 126) or (128 <= byte <= 255):
                current_word += bytes([byte])
            # Whitespace (tab, newline, CR, space, null)
            elif byte in (0, 9, 10, 13, 32):
                if current_word and len(current_word) > 2:
                    try:
                        word = current_word.decode('latin-1', errors='ignore').strip()
                        if word and self._is_likely_word(word):
                            words.append(word)
                    except:
                        pass
                current_word = b''
            else:
                current_word = b''
        
        # Don't forget the last word
        if current_word and len(current_word) > 2:
            try:
                word = current_word.decode('latin-1', errors='ignore').strip()
                if word and self._is_likely_word(word):
                    words.append(word)
            except:
                pass
        
        return ' '.join(words) if words else ""
    
    def _extract_ascii_strings(self, content: bytes, min_len: int = 4) -> str:
        """Extract continuous ASCII/printable strings.
        
        Look for sequences of printable characters.
        
        Args:
            content: Binary content
            min_len: Minimum string length to extract
            
        Returns:
            str: Extracted text
        """
        strings = []
        current = b''
        
        for byte in content:
            # Printable ASCII
            if 32 <= byte <= 126:
                current += bytes([byte])
            else:
                if len(current) >= min_len:
                    try:
                        s = current.decode('ascii', errors='ignore').strip()
                        if s and self._is_likely_word(s):
                            strings.append(s)
                    except:
                        pass
                current = b''
        
        # Last one
        if len(current) >= min_len:
            try:
                s = current.decode('ascii', errors='ignore').strip()
                if s and self._is_likely_word(s):
                    strings.append(s)
            except:
                pass
        
        return ' '.join(strings) if strings else ""
    
    @staticmethod
    def _is_likely_word(text: str) -> bool:
        """Check if text is likely a real word (not garbage).
        
        Filters out:
        - Only numbers/symbols
        - Only repeated characters
        - Known junk patterns
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if likely a real word
        """
        if not text:
            return False
        
        # Skip if only digits or symbols
        if not any(c.isalpha() for c in text):
            return False
        
        # Skip if all same character
        if len(set(text)) <= 1:
            return False
        
        # Skip known garbage patterns
        if re.match(r'^[\W\d_]{3,}$', text):
            return False
        
        # Skip too short or too long
        if len(text) < 2 or len(text) > 100:
            return False
        
        return True
