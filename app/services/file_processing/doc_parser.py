"""Specialized parser for old MS Word .doc binary format.

Uses Aspose.Words for robust .doc parsing without external dependencies (LibreOffice/Antiword).
This is a pure Python solution (via pip) that works in the cloud.
"""

import logging
from pathlib import Path
from typing import Optional

# Try to import aspose.words, handle if missing
try:
    import aspose.words as aw
except ImportError:
    aw = None

logger = logging.getLogger(__name__)


class DOCParser:
    """Specialized parser for old binary .doc format using Aspose.Words.
    
    This solution:
    1. Does NOT require LibreOffice or Antiword
    2. Installs via pip (aspose-words)
    3. Works on Windows/Linux/macOS automatically
    4. Handles encodings (Russian CP1251) correctly
    """
    
    def __init__(self) -> None:
        if aw is None:
            logger.warning("⚠ aspose-words not installed. DOC parsing will fail.")
            logger.warning("pip install aspose-words")
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from .doc file using Aspose.Words.
        
        Args:
            file_path: Path to .doc file
            
        Returns:
            str: Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If extraction fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if aw is None:
            raise ValueError("aspose-words library is missing. Run: pip install aspose-words")
        
        logger.info(f"Extracting text from {file_path.name} using Aspose.Words...")
        
        try:
            # Load document
            # Aspose automatically detects format and encoding
            doc = aw.Document(str(file_path))
            
            # Extract text
            text = doc.get_text()
            
            # Clean up evaluation watermark if present
            # Aspose adds: "Evaluation Only. Created with Aspose.Words..."
            if "Evaluation Only. Created with Aspose.Words." in text:
                logger.info("Removing Aspose evaluation watermark")
                text = text.replace("Evaluation Only. Created with Aspose.Words. Copyright 2003-2023 Aspose Pty Ltd.", "")
                # Remove common header/footer evaluation artifacts
                lines = text.splitlines()
                cleaned_lines = [
                    line for line in lines 
                    if "Created with Aspose.Words" not in line 
                    and "Evaluation Only" not in line
                ]
                text = "\n".join(cleaned_lines)
            
            if text and text.strip():
                logger.info(f"✓ Aspose extraction successful: {len(text)} chars")
                return text.strip()
            else:
                raise ValueError("Extracted text is empty")
                
        except Exception as e:
            logger.error(f"Aspose extraction error: {e}")
            raise ValueError(f"Failed to extract text from .doc: {e}")
