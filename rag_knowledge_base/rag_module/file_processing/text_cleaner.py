"""Text cleaning and normalization for extracted document content for RAG.

Handles cleanup of extracted text from binary .doc files and other sources.
Removes garbage characters, normalizes whitespace, and preserves readability.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TextCleaner:
    """Clean and normalize extracted text from documents.
    
    Handles:
    - Removal of control characters
    - Normalization of whitespace
    - Filtering of garbage lines
    - Preservation of document structure
    """
    
    MIN_WORD_LENGTH = 2
    MAX_WORD_LENGTH = 100
    MIN_LINE_LENGTH = 3
    
    @classmethod
    def clean_extracted_text(cls, text: str, aggressive: bool = False) -> str:
        """Clean extracted text from binary/corrupted documents.
        
        Args:
            text: Raw extracted text
            aggressive: If True, more aggressive cleaning (may lose some data)
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        original_len = len(text)
        logger.info(f"Cleaning text ({original_len} chars, aggressive={aggressive})")
        
        text = cls._remove_control_chars(text)
        text = cls._decode_escaped_chars(text)
        text = cls._normalize_whitespace(text)
        text = cls._remove_garbage_lines(text)
        text = cls._fix_word_boundaries(text)
        
        if aggressive:
            text = cls._aggressive_cleanup(text)
        
        text = cls._normalize_whitespace(text)
        
        cleaned_len = len(text)
        reduction = round((1 - cleaned_len / max(original_len, 1)) * 100, 1)
        logger.info(f"Text cleaned: {original_len} → {cleaned_len} chars (-{reduction}%)")
        
        return text.strip()
    
    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """Remove control characters and invalid UTF-8."""
        result = []
        for char in text:
            code = ord(char)
            if code < 32 and code not in (9, 10, 13):
                continue
            if 127 <= code < 160:
                continue
            if code > 65535:
                continue
            result.append(char)
        return ''.join(result)
    
    @staticmethod
    def _decode_escaped_chars(text: str) -> str:
        """Decode common escaped/mangled character sequences."""
        replacements = {
            'Ã': '',
            '\x00': '',
            '\r\n': '\n',
            '\r': '\n',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace while preserving paragraphs."""
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\n+', '\n\n', text)
        text = re.sub(r' +\n', '\n', text)
        text = re.sub(r'\n +', '\n', text)
        return text
    
    @staticmethod
    def _remove_garbage_lines(text: str) -> str:
        """Remove lines that are pure garbage."""
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            if not line.strip():
                clean_lines.append('')
                continue
            
            if len(line.strip()) < TextCleaner.MIN_LINE_LENGTH:
                continue
            
            letters = sum(1 for c in line if c.isalpha())
            non_letters = len(line) - letters
            
            if letters > 0 and non_letters / len(line) > 0.8:
                continue
            
            if len(set(line.strip())) <= 1:
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    @staticmethod
    def _fix_word_boundaries(text: str) -> str:
        """Fix broken word boundaries from binary extraction."""
        return text
    
    @staticmethod
    def _aggressive_cleanup(text: str) -> str:
        """More aggressive cleaning (may lose some valid data)."""
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            letters = sum(1 for c in line if c.isalpha())
            if len(line) > 0 and letters / len(line) < 0.3:
                continue
            
            digits = sum(1 for c in line if c.isdigit())
            if digits / max(len(line), 1) > 0.5:
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    @classmethod
    def is_text_usable(cls, text: str, min_length: int = 50) -> bool:
        """Check if extracted text is usable quality."""
        if not text:
            return False
        
        if len(text.strip()) < min_length:
            logger.warning(f"Text too short: {len(text)} chars < {min_length} required")
            return False
        
        letters = sum(1 for c in text if c.isalpha())
        if letters / len(text) < 0.1:
            logger.warning(f"Text has too few letters: {letters}/{len(text)}")
            return False
        
        logger.info(f"Text quality OK: {len(text)} chars, {letters} letters ({round(letters/len(text)*100)}%)")
        return True
    
    @classmethod
    def get_preview(cls, text: str, max_lines: int = 5) -> str:
        """Get preview of cleaned text for debugging."""
        lines = text.split('\n')
        preview_lines = [l for l in lines[:max_lines] if l.strip()]
        preview = '\n'.join(preview_lines[:max_lines])
        
        if len(lines) > max_lines:
            preview += f"\n... ({len(lines) - max_lines} more lines)"
        
        return preview
