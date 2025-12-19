"""Text splitter utility for Telegram message limits.

Handles splitting long text into multiple messages respecting
Telegram's 4096 character limit.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

TG_MAX_MESSAGE_LENGTH = 4096
IDEAL_CHUNK_SIZE = 3900  # Slightly less to be safe


class TextSplitter:
    """Splits long text into Telegram-compatible chunks.
    
    Tries to split on sentence boundaries to preserve readability.
    Falls back to word boundaries if necessary.
    """
    
    def __init__(self, max_length: int = TG_MAX_MESSAGE_LENGTH) -> None:
        """Initialize text splitter.
        
        Args:
            max_length: Maximum length per message (default: Telegram limit)
        """
        self.max_length = max_length
    
    def split(
        self,
        text: str,
        strategy: str = "sentence",
    ) -> list[str]:
        """Split text into chunks.
        
        Args:
            text: Text to split
            strategy: Splitting strategy ('sentence', 'paragraph', or 'word')
            
        Returns:
            list[str]: List of text chunks
            
        Example:
            >>> splitter = TextSplitter()
            >>> chunks = splitter.split("Long text...")
            >>> for i, chunk in enumerate(chunks):
            ...     print(f"Chunk {i+1}: {len(chunk)} chars")
        """
        if len(text) <= self.max_length:
            return [text]
        
        if strategy == "sentence":
            return self._split_by_sentence(text)
        elif strategy == "paragraph":
            return self._split_by_paragraph(text)
        else:
            return self._split_by_word(text)
    
    def _split_by_sentence(self, text: str) -> list[str]:
        """Split text by sentence boundaries.
        
        Attempts to split on periods, question marks, and exclamation marks.
        Falls back to word splitting if sentences are too long.
        """
        chunks: list[str] = []
        current_chunk = ""
        
        # Split by common sentence endings
        sentences = text.replace("!\n", "!|").replace("?\n", "?|").replace(".\n", ".|")
        sentences = sentences.replace("!", "!|").replace("?", "?|").replace(".", ".")
        sentences = [s.strip() for s in sentences.split("|") if s.strip()]
        
        for sentence in sentences:
            test_chunk = current_chunk + sentence + " "
            
            if len(test_chunk) <= self.max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single sentence is too long, split it by words
                if len(sentence) > self.max_length:
                    word_chunks = self._split_by_word(sentence)
                    chunks.extend(word_chunks[:-1])
                    current_chunk = word_chunks[-1] + " "
                else:
                    current_chunk = sentence + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        logger.debug(f"Split into {len(chunks)} chunks by sentence")
        return chunks
    
    def _split_by_paragraph(self, text: str) -> list[str]:
        """Split text by paragraph boundaries.
        
        Assumes paragraphs are separated by double newlines.
        """
        chunks: list[str] = []
        current_chunk = ""
        
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        for paragraph in paragraphs:
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(test_chunk) <= self.max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph is too long, split by sentence
                if len(paragraph) > self.max_length:
                    para_chunks = self._split_by_sentence(paragraph)
                    chunks.extend(para_chunks[:-1])
                    current_chunk = para_chunks[-1]
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.debug(f"Split into {len(chunks)} chunks by paragraph")
        return chunks
    
    def _split_by_word(self, text: str) -> list[str]:
        """Split text by word boundaries.
        
        Most aggressive strategy, used as fallback.
        """
        chunks: list[str] = []
        current_chunk = ""
        
        words = text.split()
        
        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            
            if len(test_chunk) <= self.max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.debug(f"Split into {len(chunks)} chunks by word")
        return chunks
    
    def count_messages(self, text: str) -> int:
        """Count how many messages would be needed for text.
        
        Args:
            text: Text to analyze
            
        Returns:
            int: Number of messages needed
        """
        if len(text) <= self.max_length:
            return 1
        
        return (len(text) + self.max_length - 1) // self.max_length
