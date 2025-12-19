"""File processing converter orchestrator.

Coordinates extraction of text from various file formats (PDF, DOCX, ZIP).
Handles file routing to appropriate parser.
"""

import logging
from pathlib import Path
from typing import Optional

from app.services.file_processing.pdf_parser import PDFParser
from app.services.file_processing.docx_parser import DOCXParser
from app.services.file_processing.zip_handler import ZIPHandler

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".zip", ".doc"}


class FileConverter:
    """Converter for extracting text from various file formats.
    
    Supports: PDF, DOCX, TXT, ZIP archives
    Delegates to specialized parsers for each format.
    """
    
    def __init__(self) -> None:
        """Initialize converter with parsers."""
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()
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
        For ZIP files, extracts supported files and combines text.
        
        Args:
            file_path: Path to file
            temp_dir: Directory for temporary files (required for ZIP)
            
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
            raise ValueError(
                f"Unsupported format: {file_path.suffix}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        file_suffix = file_path.suffix.lower()
        
        try:
            if file_suffix == ".pdf":
                logger.info(f"Processing PDF: {file_path.name}")
                return self.pdf_parser.extract_text(file_path)
            
            elif file_suffix == ".docx":
                logger.info(f"Processing DOCX: {file_path.name}")
                return self.docx_parser.extract_text(file_path)
            
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
