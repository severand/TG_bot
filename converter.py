"""File processing converter orchestrator.

Coordinates extraction of text from various file formats (PDF, DOCX, ZIP, Excel, DOC).
Handles file routing to appropriate parser.

Fixes 2025-12-21 00:30:
- CRITICAL: Old .doc IS BINARY, NOT ZIP!
- Added proper detection: try as .docx first (ZIP), if fails = binary .doc
- .doc files now handled by DOCXParser with binary fallback
- Never route .doc to ZIP handler (that was the bug!)
- DOCXParser now has improved binary extraction

Fixes 2025-12-20 23:41:
- ОЧЕНЬ ПРОСТО: .doc -> .docx это то же самое
- .doc это ZIP-архив с XML внутри
- .docx это тоже ZIP-архив с XML
- Просто переименовываем файл, и всё!
- Ni LibreOffice, no subprocess - только питон

Fixes 2025-12-20 22:10:
- Добавлена поддержка Excel файлов (.xlsx, .xls)
- Используется openpyxl и xlrd для парсинга таблиц
- Логирование ошибок формата улучшено
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from rag_module.file_processing.pdf_parser import PDFParser
from rag_module.file_processing.docx_parser import DOCXParser
from rag_module.file_processing.excel_parser import ExcelParser
from rag_module.file_processing.zip_handler import ZIPHandler

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".zip", ".doc", ".xlsx", ".xls"}


class FileConverter:
    """Converter for extracting text from various file formats.
    
    Supports: PDF, DOCX, TXT, ZIP archives, Excel (.xlsx, .xls), Old .doc
    
    IMPORTANT: Old .doc files are BINARY format (not ZIP like .docx).
    Delegates to specialized parsers for each format.
    """
    
    def __init__(self) -> None:
        """Initialize converter with parsers."""
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()
        self.excel_parser = ExcelParser()
        self.zip_handler = ZIPHandler()
    
    def is_supported(self, file_path: Path) -> bool:
        """Check if file format is supported.
        
        Args:
            file_path: Path to file
            
        Returns:
            bool: True if format is supported
        """
        return file_path.suffix.lower() in SUPPORTED_FORMATS
    
    def extract_text(
        self,
        file_path: Path,
        temp_dir: Optional[Path] = None,
    ) -> str:
        """Extract text from file.
        
        Routes to appropriate parser based on file format.
        For .doc files: tries as ZIP first (newer hybrid format), 
                       then falls back to binary (old MS Word format)
        For ZIP files: extracts supported files and combines text.
        
        Args:
            file_path: Path to file
            temp_dir: Directory for temporary files (required for ZIP and .doc)
            
        Returns:
            str: Extracted text
            
        Raises:
            ValueError: If format is not supported
            FileNotFoundError: If file doesn't exist
            
        Example:
            >>> converter = FileConverter()
            >>> text = converter.extract_text(Path("document.pdf"))
            >>> print(f"Extracted {len(text)} characters")
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.is_supported(file_path):
            supported_str = ", ".join(sorted(SUPPORTED_FORMATS))
            raise ValueError(
                f"Unsupported format: {file_path.suffix}. "
                f"Supported: {supported_str}"
            )
        
        file_suffix = file_path.suffix.lower()
        
        try:
            # Handle .doc files (can be ZIP-like or binary)
            # CRITICAL: Old .doc is BINARY, not ZIP!
            if file_suffix == ".doc":
                logger.info(f"Processing .doc file: {file_path.name}")
                if not temp_dir:
                    raise ValueError("temp_dir required for .doc processing")
                
                # Try to process directly with DOCX parser
                # (it has ZIP try + binary fallback)
                logger.info(f"Attempting to extract from .doc as {file_path.name}")
                return self.docx_parser.extract_text(file_path)
            
            # Regular format routing
            if file_suffix == ".pdf":
                logger.info(f"Processing PDF: {file_path.name}")
                return self.pdf_parser.extract_text(file_path)
            
            elif file_suffix == ".docx":
                logger.info(f"Processing DOCX: {file_path.name}")
                return self.docx_parser.extract_text(file_path)
            
            elif file_suffix in {".xlsx", ".xls"}:
                logger.info(f"Processing Excel: {file_path.name}")
                return self.excel_parser.extract_text(file_path)
            
            elif file_suffix == ".txt":
                logger.info(f"Processing TXT: {file_path.name}")
                return self._extract_text_file(file_path)
            
            elif file_suffix == ".zip":
                if not temp_dir:
                    raise ValueError("temp_dir required for ZIP processing")
                logger.info(f"Processing ZIP: {file_path.name}")
                return self._extract_zip(file_path, temp_dir)
            
            else:
                raise ValueError(f"Unsupported format: {file_suffix}")
        
        except Exception as e:
            logger.error(f"Error extracting text from {file_path.name}: {e}")
            raise
    
    def _extract_text_file(self, file_path: Path) -> str:
        """Extract text from plain text file.
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            str: File content
        """
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed for {file_path.name}, trying latin-1")
            return file_path.read_text(encoding="latin-1")
    
    def _extract_zip(self, file_path: Path, temp_dir: Path) -> str:
        """Extract and process ZIP archive.
        
        Args:
            file_path: Path to ZIP file
            temp_dir: Directory for temporary files
            
        Returns:
            str: Combined text from all extracted files
        """
        extracted_files = self.zip_handler.extract_supported_files(
            file_path,
            temp_dir,
        )
        
        if not extracted_files:
            logger.warning(f"No supported files found in {file_path.name}")
            return ""
        
        combined_text: list[str] = []
        
        for file_path_extracted in extracted_files:
            try:
                text = self.extract_text(file_path_extracted, temp_dir)
                if text:
                    combined_text.append(
                        f"\n\n=== File: {file_path_extracted.name} ===\n{text}"
                    )
            except Exception as e:
                logger.warning(f"Error processing {file_path_extracted.name}: {e}")
                continue
        
        return "".join(combined_text)
