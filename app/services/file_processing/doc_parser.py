"""Specialized parser for old MS Word .doc binary format.

Uses antiword utility for reliable text extraction from .doc files.
antword is a proven tool that works with old MS Word 97-2003 format.

Installation:
- Windows: choco install antiword
- Linux: sudo apt-get install antiword
- macOS: brew install antiword
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DOCParser:
    """Specialized parser for old binary .doc format using antiword.
    
    Old MS Word .doc files (97-2003) use OLE compound file format.
    We use antiword utility which is proven and reliable.
    
    Handles:
    - Old .doc format (Word 97-2003)
    - Binary OLE files
    - Automatic fallback if antiword not installed
    """
    
    def __init__(self) -> None:
        self._antiword_available = self._check_antiword()
    
    @staticmethod
    def _check_antiword() -> bool:
        """Check if antiword is installed."""
        try:
            subprocess.run(
                ["antiword", "-v"],
                capture_output=True,
                timeout=5
            )
            logger.info("✓ antiword is installed and available")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠ antiword is NOT installed")
            logger.warning("Install it:")
            logger.warning("  Windows: choco install antiword")
            logger.warning("  Linux: sudo apt-get install antiword")
            logger.warning("  macOS: brew install antiword")
            return False
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from old binary .doc file using antiword.
        
        Args:
            file_path: Path to .doc file
            
        Returns:
            str: Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If antiword not installed or extraction fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self._antiword_available:
            raise ValueError(
                "antiword is not installed. Install it: "
                "Windows (choco install antiword), "
                "Linux (apt-get install antiword), "
                "macOS (brew install antiword)"
            )
        
        logger.info(f"Extracting text from {file_path.name} ({file_path.stat().st_size} bytes)")
        
        try:
            result = subprocess.run(
                ["antiword", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                text = result.stdout.strip()
                if text:
                    logger.info(f"✓ antiword extraction successful: {len(text)} chars")
                    return text
                else:
                    logger.warning(f"antiword returned empty text")
                    raise ValueError(f"No text extracted from {file_path.name}")
            else:
                logger.error(f"antiword failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"antiword error: {result.stderr[:200]}")
                raise ValueError(f"Cannot extract text from {file_path.name}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"antiword conversion timed out for {file_path.name}")
            raise ValueError(f"Extraction timeout for {file_path.name}")
        except Exception as e:
            logger.error(f"Extraction error: {type(e).__name__}: {str(e)[:100]}")
            raise ValueError(f"Cannot extract text from {file_path.name}") from e
