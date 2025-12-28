"""
Unified OCR Service

Provides consistent OCR across ALL modes:
- Local Tesseract (primary)
- EasyOCR (fallback)
- NO API calls (no SSL issues)

Usage:
    from app.services.ocr import OCRService
    ocr = OCRService()
    text = await ocr.extract_from_file(image_path)
    text = await ocr.extract_from_bytes(image_bytes)
"""

from .ocr_service import OCRService, OCRQualityLevel

__all__ = ['OCRService', 'OCRQualityLevel']
