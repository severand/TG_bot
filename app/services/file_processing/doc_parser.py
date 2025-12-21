"""Specialized parser for old MS Word .doc binary format.

Handles extraction of text from old Microsoft Word .doc files (pre-2007).
Old .doc files use OLE (Object Linking and Embedding) compound binary format,
not ZIP like modern .docx files.

This parser provides specialized extraction methods optimized for binary .doc format.
Now with automatic encoding detection (CP1251 for Russian, UTF-16 LE, etc).
"""

import logging
import re
from pathlib import Path
from typing import Optional

try:
    import chardet
except ImportError:
    chardet = None

logger = logging.getLogger(__name__)


def _get_text_preview(text: str, max_words: int = 150) -> str:
    """Получить предпросмотр текста.
    
    Args:
        text: Исходный текст
        max_words: Максимальное количество слов
        
    Returns:
        Предпросмотр текста
    """
    if not text or not text.strip():
        return "(empty)"
    
    words = text.split()
    if len(words) <= max_words:
        return text.strip()[:800]
    
    preview = ' '.join(words[:max_words])
    return preview[:800] + "..."


class DOCParser:
    """Specialized parser for old binary .doc format.
    
    Old MS Word .doc files (97-2003) use OLE compound file format.
    This is completely different from modern .docx (which is ZIP-based).
    
    Handles:
    - OLE format detection
    - Automatic encoding detection (CP1251, UTF-16 LE, UTF-8, etc)
    - Text extraction from binary Word format
    - Multiple fallback strategies
    - Corrupted file recovery
    """
    
    # OLE signature (first 8 bytes of OLE files)
    OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from old binary .doc file.
        
        Uses multiple extraction strategies:
        1. Detect encoding (CP1251 for Russian, UTF-16 LE, etc)
        2. Look for text blocks in detected encoding
        3. Fallback: Try multiple encodings
        
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
        
        # DETECT ENCODING
        detected_encoding = self._detect_encoding(content)
        logger.info(f"Detected encoding: {detected_encoding}")
        
        # Try multiple extraction methods with encoding-aware approach
        results = []
        
        # Method 1: Try with detected encoding first
        if detected_encoding:
            text = self._extract_with_encoding(content, detected_encoding)
            if text and len(text.strip()) > 20:
                results.append((f"Detected ({detected_encoding})", len(text), text))
                logger.debug(f"Detected encoding extraction found {len(text)} chars")
        
        # Method 2: Try CP1251 (Russian)
        text = self._extract_with_encoding(content, 'cp1251')
        if text and len(text.strip()) > 20:
            results.append(("CP1251 (Russian)", len(text), text))
            logger.debug(f"CP1251 extraction found {len(text)} chars")
        
        # Method 3: Try UTF-16 LE
        text = self._extract_unicode_strings(content)
        if text and len(text.strip()) > 20:
            results.append(("Unicode (UTF-16 LE)", len(text), text))
            logger.debug(f"Unicode extraction found {len(text)} chars")
        
        # Method 4: Try null-separated blocks (ASCII-safe)
        text = self._extract_null_blocks(content)
        if text and len(text.strip()) > 20:
            results.append(("Null-blocks (ASCII)", len(text), text))
            logger.debug(f"Null-block extraction found {len(text)} chars")
        
        # Choose best result (by length AND quality)
        if results:
            # Prefer methods with detected encoding / CP1251
            results.sort(key=lambda x: (x[1], -1 if 'Detected' in x[0] or 'CP1251' in x[0] else 0), reverse=True)
            best_method, best_len, best_text = results[0]
            logger.info(f"✓ Best extraction: {best_method} ({best_len} chars)")
            
            preview = _get_text_preview(best_text, max_words=150)
            logger.info(f"📝 TEXT PREVIEW ({best_method}, first 150 words):\n{preview}")
            
            return best_text.strip()
        
        logger.warning(f"No substantial text found in {file_path.name}")
        return ""
    
    def _is_ole_file(self, content: bytes) -> bool:
        """Check if file is OLE format (old .doc)."""
        if len(content) >= 8:
            return content[:8] == self.OLE_SIGNATURE
        return False
    
    def _detect_encoding(self, content: bytes) -> Optional[str]:
        """Detect file encoding using chardet.
        
        Returns:
            str: Detected encoding (e.g., 'cp1251', 'utf-8')
        """
        if chardet is None:
            logger.debug("chardet not installed, skipping encoding detection")
            return None
        
        try:
            # Use first 100KB for detection
            sample = content[:min(100000, len(content))]
            result = chardet.detect(sample)
            
            if result and result.get('encoding'):
                confidence = result.get('confidence', 0)
                encoding = result['encoding']
                logger.debug(f"chardet detected: {encoding} (confidence: {confidence:.2%})")
                
                # Only trust high-confidence results
                if confidence > 0.7:
                    return encoding
        except Exception as e:
            logger.debug(f"Encoding detection failed: {e}")
        
        return None
    
    def _extract_with_encoding(self, content: bytes, encoding: str) -> str:
        """Extract text using specific encoding.
        
        Args:
            content: Binary content
            encoding: Encoding to try (e.g., 'cp1251', 'utf-8')
            
        Returns:
            str: Extracted text
        """
        try:
            decoded = content.decode(encoding, errors='ignore')
            
            # Remove control characters but keep Cyrillic and other valid chars
            text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', decoded)
            text = re.sub(r' +', ' ', text)  # Collapse whitespace
            
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug(f"Extraction with {encoding} failed: {e}")
        
        return ""
    
    def _extract_unicode_strings(self, content: bytes) -> str:
        """Extract UTF-16 LE encoded strings.
        
        Modern MS Word stores text in UTF-16 LE encoding.
        """
        try:
            decoded = content.decode('utf-16-le', errors='ignore')
            text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', decoded)
            text = re.sub(r' +', ' ', text)
            
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug(f"Unicode extraction failed: {e}")
        
        return ""
    
    def _extract_null_blocks(self, content: bytes) -> str:
        """Extract text from null-separated blocks.
        
        In binary .doc format, text often appears in blocks separated by null bytes.
        """
        words = []
        current_word = b''
        
        for byte in content:
            if (32 <= byte <= 126) or (128 <= byte <= 255):
                current_word += bytes([byte])
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
        
        if current_word and len(current_word) > 2:
            try:
                word = current_word.decode('latin-1', errors='ignore').strip()
                if word and self._is_likely_word(word):
                    words.append(word)
            except:
                pass
        
        return ' '.join(words) if words else ""
    
    @staticmethod
    def _is_likely_word(text: str) -> bool:
        """Check if text is likely a real word (not garbage)."""
        if not text:
            return False
        
        if not any(c.isalpha() for c in text):
            return False
        
        if len(set(text)) <= 1:
            return False
        
        if re.match(r'^[\W\d_]{3,}$', text):
            return False
        
        if len(text) < 2 or len(text) > 100:
            return False
        
        return True
