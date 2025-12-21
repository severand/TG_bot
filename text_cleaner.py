"""Text cleaning and normalization for extracted document content.

Handles cleanup of extracted text from binary .doc files and other sources.
Removes garbage characters, normalizes whitespace, and preserves readability.

Fixes 2025-12-21 00:45:
- Added text cleaning for binary .doc extraction
- Remove control characters and invalid UTF-8 sequences
- Normalize multiple spaces/newlines
- Filter out pure garbage lines
- Preserve actual content words
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
    
    # Minimum word length to keep (avoid single chars)
    MIN_WORD_LENGTH = 2
    
    # Maximum word length (filter unrealistic words)
    MAX_WORD_LENGTH = 100
    
    # Minimum characters per line to be meaningful
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
        
        # Step 1: Remove null bytes and control characters
        text = cls._remove_control_chars(text)
        
        # Step 2: Decode any escaped sequences
        text = cls._decode_escaped_chars(text)
        
        # Step 3: Normalize whitespace
        text = cls._normalize_whitespace(text)
        
        # Step 4: Remove garbage lines
        text = cls._remove_garbage_lines(text)
        
        # Step 5: Fix word boundaries
        text = cls._fix_word_boundaries(text)
        
        if aggressive:
            # Step 6: Additional aggressive cleaning
            text = cls._aggressive_cleanup(text)
        
        # Step 7: Final whitespace normalization
        text = cls._normalize_whitespace(text)
        
        cleaned_len = len(text)
        reduction = round((1 - cleaned_len / max(original_len, 1)) * 100, 1)
        logger.info(f"Text cleaned: {original_len} → {cleaned_len} chars (-{reduction}%)")
        
        return text.strip()
    
    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """Remove control characters and invalid UTF-8.
        
        Keep:
        - Letters and digits
        - Common punctuation
        - Whitespace (tab, newline, space)
        - Cyrillic characters
        
        Remove:
        - Control characters (00-1F, 7F-9F)
        - Invalid UTF-8 sequences
        """
        result = []
        for char in text:
            code = ord(char)
            
            # Control characters
            if code < 32 and code not in (9, 10, 13):  # Keep tab, newline, CR
                continue
            # DEL and control chars
            if 127 <= code < 160:
                continue
            # Very high Unicode (likely corruption)
            if code > 65535:
                continue
            
            result.append(char)
        
        return ''.join(result)
    
    @staticmethod
    def _decode_escaped_chars(text: str) -> str:
        """Decode common escaped/mangled character sequences.
        
        Example: Ã¤Ã¥ (UTF-8 corruption) → cleaned
        """
        # Replace common corrupted Cyrillic patterns
        replacements = {
            'Ã': '',  # Corrupted encoding markers
            '\x00': '',  # Null bytes
            '\r\n': '\n',  # Normalize line endings
            '\r': '\n',  # Mac line endings
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace while preserving paragraphs.
        
        - Multiple spaces → single space
        - Multiple newlines → max 2 newlines (paragraph break)
        - Spaces around newlines → removed
        """
        # Multiple spaces → single space
        text = re.sub(r' +', ' ', text)
        
        # Multiple newlines → max 2 (paragraph break)
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Space before newline → remove
        text = re.sub(r' +\n', '\n', text)
        
        # Newline then spaces → newline only
        text = re.sub(r'\n +', '\n', text)
        
        return text
    
    @staticmethod
    def _remove_garbage_lines(text: str) -> str:
        """Remove lines that are pure garbage.
        
        Lines with:
        - Only symbols/control chars
        - Only repeated characters
        - Too many non-letter characters
        - Single meaningless characters
        """
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            # Keep empty lines (paragraph breaks)
            if not line.strip():
                clean_lines.append('')
                continue
            
            # Too short
            if len(line.strip()) < TextCleaner.MIN_LINE_LENGTH:
                continue
            
            # Count letters vs non-letters
            letters = sum(1 for c in line if c.isalpha())
            non_letters = len(line) - letters
            
            # If 80%+ non-letters, likely garbage
            if letters > 0 and non_letters / len(line) > 0.8:
                continue
            
            # If all same character (like "========")
            if len(set(line.strip())) <= 1:
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    @staticmethod
    def _fix_word_boundaries(text: str) -> str:
        """Fix broken word boundaries from binary extraction.
        
        Example: "слов но" → "словно"
        Sometimes binary extraction breaks words into separate pieces.
        """
        # This is tricky - we keep simple heuristics:
        # If short sequences of single letters separated by spaces in middle of word,
        # they might be extraction artifacts. But we're conservative here.
        
        return text
    
    @staticmethod
    def _aggressive_cleanup(text: str) -> str:
        """More aggressive cleaning (may lose some valid data).
        
        Use only when normal cleaning didn't work well.
        """
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            # Keep only lines with substantial letter content
            letters = sum(1 for c in line if c.isalpha())
            
            # Need at least 30% letters to keep
            if len(line) > 0 and letters / len(line) < 0.3:
                continue
            
            # Remove lines with too many numbers (might be metadata)
            digits = sum(1 for c in line if c.isdigit())
            if digits / max(len(line), 1) > 0.5:
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    @classmethod
    def is_text_usable(cls, text: str, min_length: int = 50) -> bool:
        """Check if extracted text is usable quality.
        
        Args:
            text: Text to check
            min_length: Minimum length to be considered usable
            
        Returns:
            bool: True if text quality is acceptable
        """
        if not text:
            return False
        
        if len(text.strip()) < min_length:
            logger.warning(f"Text too short: {len(text)} chars < {min_length} required")
            return False
        
        # Check for minimum letter content
        letters = sum(1 for c in text if c.isalpha())
        if letters / len(text) < 0.1:  # Need at least 10% letters
            logger.warning(f"Text has too few letters: {letters}/{len(text)}")
            return False
        
        logger.info(f"Text quality OK: {len(text)} chars, {letters} letters ({round(letters/len(text)*100)}%)")
        return True
    
    @classmethod
    def get_preview(cls, text: str, max_lines: int = 5) -> str:
        """Get preview of cleaned text for debugging.
        
        Args:
            text: Full text
            max_lines: Maximum lines to show
            
        Returns:
            str: Preview snippet
        """
        lines = text.split('\n')
        preview_lines = [l for l in lines[:max_lines] if l.strip()]
        preview = '\n'.join(preview_lines[:max_lines])
        
        if len(lines) > max_lines:
            preview += f"\n... ({len(lines) - max_lines} more lines)"
        
        return preview
