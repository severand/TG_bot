"""
OCR Service Implementation

Unified OCR for all application modes:
- conversation.py (document analysis)
- documents.py (chat mode)
- homework.py (homework mode)

Features:
- LOCAL Tesseract (primary, fast, no SSL issues)
- LOCAL EasyOCR (fallback)
- Quality detection (gibberish, handwriting)
- Consistent error handling
"""

import logging
import os
from pathlib import Path
from enum import Enum
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)

# Try import Tesseract
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image
    
    # Windows: Auto-detect Tesseract installation
    if os.name == 'nt':
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"[OCR] Found Tesseract at: {path}")
                break
    
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    logger.info("[OCR] ✅ Tesseract available")
except Exception as e:
    logger.warning(f"[OCR] Tesseract NOT available: {e}")
    TESSERACT_AVAILABLE = False

# Try import EasyOCR
EASYOCR_AVAILABLE = False
_easyocr_reader = None
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    logger.info("[OCR] ✅ EasyOCR available as fallback")
except ImportError:
    logger.warning("[OCR] EasyOCR NOT available")
    EASYOCR_AVAILABLE = False


class OCRQualityLevel(Enum):
    """OCR result quality assessment."""
    EXCELLENT = "excellent"  # Clean, clear text
    GOOD = "good"  # Recognizable, some errors
    POOR = "poor"  # Gibberish, handwriting, low quality
    FAILED = "failed"  # No text detected


class OCRService:
    """
    Unified OCR Service for all application modes.
    
    Uses LOCAL OCR engines only (no API calls):
    1. Tesseract (primary) - fast, accurate for printed text
    2. EasyOCR (fallback) - better for non-Latin, handles rotation
    
    NEVER uses OCR.space or any remote API (SSL issues).
    """
    
    def __init__(self):
        """Initialize OCR service."""
        self.tesseract_available = TESSERACT_AVAILABLE
        self.easyocr_available = EASYOCR_AVAILABLE
        self._easyocr_reader = None
        
        if not (self.tesseract_available or self.easyocr_available):
            logger.error(
                "[OCR] ❌ NO OCR ENGINE AVAILABLE!\n"
                "Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Or run: pip install easyocr"
            )
    
    async def extract_from_file(
        self,
        file_path: Path,
        user_id: int = None,
    ) -> tuple[str, OCRQualityLevel]:
        """
        Extract text from image file.
        
        Args:
            file_path: Path to image file
            user_id: User ID for logging
            
        Returns:
            (extracted_text, quality_level)
        """
        try:
            if not file_path.exists():
                logger.error(f"[OCR] File not found: {file_path}")
                return "", OCRQualityLevel.FAILED
            
            logger.info(f"[OCR] Extracting from file: {file_path}")
            
            # Try Tesseract first (LOCAL, fast)
            if self.tesseract_available:
                text = await self._tesseract_extract(file_path, user_id)
                if text:
                    quality = self._assess_quality(text)
                    return text, quality
            
            # Fallback to EasyOCR
            if self.easyocr_available:
                text = await self._easyocr_extract(file_path, user_id)
                if text:
                    quality = self._assess_quality(text)
                    return text, quality
            
            logger.error(f"[OCR] All OCR methods failed")
            return "", OCRQualityLevel.FAILED
        
        except Exception as e:
            logger.error(f"[OCR] Exception: {e}")
            return "", OCRQualityLevel.FAILED
    
    async def extract_from_bytes(
        self,
        image_bytes: bytes,
        user_id: int = None,
    ) -> tuple[str, OCRQualityLevel]:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Image data as bytes
            user_id: User ID for logging
            
        Returns:
            (extracted_text, quality_level)
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(image_bytes))
            
            logger.info(f"[OCR] Extracting from bytes ({len(image_bytes)} bytes)")
            
            # Try Tesseract first
            if self.tesseract_available:
                text = await self._tesseract_extract_image(image, user_id)
                if text:
                    quality = self._assess_quality(text)
                    return text, quality
            
            # Fallback to EasyOCR
            if self.easyocr_available:
                # EasyOCR needs file path, so save temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(image_bytes)
                    tmp_path = Path(tmp.name)
                
                try:
                    text = await self._easyocr_extract(tmp_path, user_id)
                    if text:
                        quality = self._assess_quality(text)
                        return text, quality
                finally:
                    tmp_path.unlink()
            
            logger.error(f"[OCR] All OCR methods failed")
            return "", OCRQualityLevel.FAILED
        
        except Exception as e:
            logger.error(f"[OCR] Exception: {e}")
            return "", OCRQualityLevel.FAILED
    
    async def _tesseract_extract(
        self,
        file_path: Path,
        user_id: int = None,
    ) -> str:
        """Extract text using Tesseract."""
        try:
            logger.info(f"[OCR] Tesseract: Starting extraction...")
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='rus+eng')
            text = text.strip()
            
            logger.info(
                f"[OCR] Tesseract: Extracted {len(text)} chars, "
                f"{len(text.split())} words"
            )
            return text
        
        except Exception as e:
            logger.warning(f"[OCR] Tesseract failed: {e}")
            return ""
    
    async def _tesseract_extract_image(
        self,
        image,
        user_id: int = None,
    ) -> str:
        """Extract text from PIL Image using Tesseract."""
        try:
            logger.info(f"[OCR] Tesseract: Starting extraction from image...")
            
            text = pytesseract.image_to_string(image, lang='rus+eng')
            text = text.strip()
            
            logger.info(
                f"[OCR] Tesseract: Extracted {len(text)} chars, "
                f"{len(text.split())} words"
            )
            return text
        
        except Exception as e:
            logger.warning(f"[OCR] Tesseract failed: {e}")
            return ""
    
    async def _easyocr_extract(
        self,
        file_path: Path,
        user_id: int = None,
    ) -> str:
        """Extract text using EasyOCR."""
        try:
            logger.info(f"[OCR] EasyOCR: Starting extraction...")
            
            # Initialize reader on first use
            if self._easyocr_reader is None:
                logger.info("[OCR] EasyOCR: Initializing reader (first time)...")
                import easyocr
                self._easyocr_reader = easyocr.Reader(['ru', 'en'])
            
            result = self._easyocr_reader.readtext(str(file_path))
            text = "\n".join([item[1] for item in result])
            text = text.strip()
            
            logger.info(
                f"[OCR] EasyOCR: Extracted {len(text)} chars, "
                f"{len(text.split())} words"
            )
            return text
        
        except Exception as e:
            logger.warning(f"[OCR] EasyOCR failed: {e}")
            return ""
    
    def _assess_quality(self, text: str) -> OCRQualityLevel:
        """
        Assess quality of extracted text.
        
        Returns:
            OCRQualityLevel indicating text quality
        """
        if not text:
            return OCRQualityLevel.FAILED
        
        word_count = len(text.split())
        char_count = len(text)
        
        # Quality heuristics
        if word_count < 5:
            logger.warning(
                f"[OCR] ⚠️ LOW WORD COUNT: {word_count} words (likely handwriting)"
            )
            return OCRQualityLevel.POOR
        
        # Check for gibberish (too many unusual characters)
        # Russian alphabet + basic Latin + common punctuation
        russian_chars = set(
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
            'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
        )
        latin_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        allowed_special = set(' .,;:!?-–—()[]{}"\'/\n\t0123456789')
        
        allowed_chars = russian_chars | latin_chars | allowed_special
        
        strange_chars = sum(1 for c in text if ord(c) > 127 and c not in allowed_chars)
        strange_ratio = strange_chars / char_count if char_count > 0 else 0
        
        if strange_ratio > 0.3:
            logger.warning(
                f"[OCR] ⚠️ HIGH GIBBERISH RATIO: {strange_ratio:.1%} "
                f"({strange_chars}/{char_count} chars)"
            )
            return OCRQualityLevel.POOR
        
        # Assess quality based on word count and gibberish
        if word_count >= 50 and strange_ratio < 0.1:
            return OCRQualityLevel.EXCELLENT
        elif word_count >= 10:
            return OCRQualityLevel.GOOD
        else:
            return OCRQualityLevel.POOR
