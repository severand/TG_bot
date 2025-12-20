"""File processing converter orchestrator.

Coordinates extraction of text from various file formats (PDF, DOCX, ZIP, Excel, DOC).
Handles file routing to appropriate parser.
AUTOMATIC .doc → .docx conversion using LibreOffice.

Fixes 2025-12-20 23:40:
- КРИТИЧЕСКОЕ: Автоматическая конвертация .doc → .docx
- Не нужно ручно конвертировать, всё выполняется автоматически
- LibreOffice в фоне конвертирует на лету
- Graceful fallback если LibreOffice не установлен

Fixes 2025-12-20 22:10:
- Добавлена поддержка Excel файлов (.xlsx, .xls)
- Используется openpyxl и xlrd для парсинга таблиц
- Логирование ошибок формата улучшено
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from app.services.file_processing.pdf_parser import PDFParser
from app.services.file_processing.docx_parser import DOCXParser
from app.services.file_processing.excel_parser import ExcelParser
from app.services.file_processing.zip_handler import ZIPHandler

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".zip", ".doc", ".xlsx", ".xls"}


class FileConverter:
    """Converter for extracting text from various file formats.
    
    Supports: PDF, DOCX, TXT, ZIP archives, Excel (.xlsx, .xls)
    Also supports old .doc files (auto-converts to .docx using LibreOffice)
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
        For ZIP files, extracts supported files and combines text.
        For .doc files, automatically converts to .docx using LibreOffice.
        
        Args:
            file_path: Path to file
            temp_dir: Directory for temporary files (required for ZIP and .doc conversion)
            
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
            # КРИТИЧЕСКОЕ: Обработка .doc файлов - конвертация в .docx
            if file_suffix == ".doc":
                logger.info(f"Processing DOC: {file_path.name}")
                if not temp_dir:
                    raise ValueError("temp_dir required for .doc conversion")
                
                # Конвертируем .doc в .docx
                docx_path = self._convert_doc_to_docx(file_path, temp_dir)
                if not docx_path:
                    raise ValueError(
                        "Failed to convert .doc file. "
                        "Install LibreOffice: pip install libreoffice or apt-get install libreoffice"
                    )
                logger.info(f"Converted to: {docx_path.name}")
                file_path = docx_path
                file_suffix = ".docx"
            
            # Обычная обработка
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
    
    def _convert_doc_to_docx(self, doc_path: Path, temp_dir: Path) -> Optional[Path]:
        """Convert .doc file to .docx using LibreOffice.
        
        Runs LibreOffice in headless mode to convert old .doc format to .docx.
        Timeout: 30 seconds per file.
        
        Args:
            doc_path: Path to .doc file
            temp_dir: Directory for output
            
        Returns:
            Path to converted .docx file, or None if conversion failed
        """
        try:
            docx_path = temp_dir / f"{doc_path.stem}.docx"
            
            logger.info(f"Converting .doc to .docx: {doc_path.name} -> {docx_path.name}")
            
            # LibreOffice команда:
            # --headless: акна в фоне
            # --convert-to docx: конвертировать в DOCX
            # --outdir: выходный каталог
            cmd = [
                "soffice",
                "--headless",
                "--convert-to", "docx",
                "--outdir", str(temp_dir),
                str(doc_path),
            ]
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            # Запускаем конверсию
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False,
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice exit code: {result.returncode}")
                logger.error(f"STDERR: {result.stderr.decode()[:300]}")
                return None
            
            # Проверяем, что файл создан
            if docx_path.exists():
                size = docx_path.stat().st_size
                logger.info(f"Conversion successful: {docx_path.name} ({size} bytes)")
                return docx_path
            else:
                logger.error(f"Output file not found: {docx_path}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice timeout for {doc_path.name}")
            return None
        except FileNotFoundError:
            logger.error(
                "LibreOffice (soffice) not found. "
                "Install: pip install libreoffice OR apt-get install libreoffice"
            )
            return None
        except Exception as e:
            logger.error(f"Conversion error: {type(e).__name__}: {e}")
            return None
    
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
