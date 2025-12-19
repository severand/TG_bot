"""ZIP archive handler module.

Handles extraction and validation of ZIP files with protection against
malicious archives (zip bombs, path traversal attacks).
"""

import logging
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".doc"}
COMPRESSION_RATIO_THRESHOLD = 100  # Max 100:1 compression ratio
MAX_FILES_IN_ARCHIVE = 500
MAX_EXTRACT_SIZE = 100 * 1024 * 1024  # 100MB


class ZipBombError(Exception):
    """Raised when zip bomb is detected."""
    pass


class ZIPHandler:
    """Handler for ZIP archives with security validation.
    
    Implements protections against:
    - Zip bombs (excessive compression ratio)
    - Path traversal attacks
    - Excessive number of files
    - Large extracted size
    """
    
    def __init__(self, max_extract_size: int = MAX_EXTRACT_SIZE) -> None:
        """Initialize ZIP handler.
        
        Args:
            max_extract_size: Maximum size of extracted archive in bytes
        """
        self.max_extract_size = max_extract_size
    
    def validate_archive(self, file_path: Path) -> bool:
        """Validate ZIP archive for security issues.
        
        Checks:
        - Archive integrity
        - Compression ratio (protection from zip bombs)
        - Number of files
        - Path traversal attempts
        
        Args:
            file_path: Path to ZIP file
            
        Returns:
            bool: True if archive is valid and safe
            
        Raises:
            ZipBombError: If malicious archive is detected
            ValueError: If archive is corrupted
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Check for corrupted files
                bad_file = zf.testzip()
                if bad_file:
                    raise ValueError(f"Corrupted file in archive: {bad_file}")
                
                # Check number of files
                if len(zf.namelist()) > MAX_FILES_IN_ARCHIVE:
                    raise ZipBombError(
                        f"Archive contains too many files ({len(zf.namelist())} > "
                        f"{MAX_FILES_IN_ARCHIVE})"
                    )
                
                # Check each file
                total_extracted_size = 0
                for info in zf.infolist():
                    # Check for path traversal
                    if ".." in info.filename or info.filename.startswith("/"):
                        raise ZipBombError(f"Path traversal detected: {info.filename}")
                    
                    # Check compression ratio
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > COMPRESSION_RATIO_THRESHOLD:
                            raise ZipBombError(
                                f"Excessive compression ratio ({ratio:.1f}:1) for "
                                f"{info.filename}"
                            )
                    
                    total_extracted_size += info.file_size
                    if total_extracted_size > self.max_extract_size:
                        raise ZipBombError(
                            f"Archive would extract to {total_extracted_size} bytes, "
                            f"exceeding limit of {self.max_extract_size}"
                        )
                
                logger.info(f"ZIP archive validated: {file_path.name}")
                return True
        
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file: {file_path.name}")
            raise ValueError(f"Invalid ZIP file: {e}") from e
    
    def extract_supported_files(
        self,
        file_path: Path,
        extract_to: Path,
    ) -> list[Path]:
        """Extract only supported file formats from ZIP.
        
        Validates archive before extraction and filters by supported formats.
        
        Args:
            file_path: Path to ZIP file
            extract_to: Directory to extract files to
            
        Returns:
            list[Path]: List of extracted supported files
            
        Raises:
            ZipBombError: If malicious archive is detected
            ValueError: If archive is corrupted
            
        Example:
            >>> handler = ZIPHandler()
            >>> files = handler.extract_supported_files(
            ...     Path("archive.zip"),
            ...     Path("./temp")
            ... )
            >>> for f in files:
            ...     print(f"Extracted: {f.name}")
        """
        # Validate before extraction
        self.validate_archive(file_path)
        
        extracted_files: list[Path] = []
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                for info in zf.infolist():
                    # Skip directories
                    if info.filename.endswith("/"):
                        continue
                    
                    # Check file extension
                    file_suffix = Path(info.filename).suffix.lower()
                    if file_suffix not in SUPPORTED_FORMATS:
                        logger.debug(
                            f"Skipping unsupported format: {info.filename}"
                        )
                        continue
                    
                    # Extract file
                    extracted_path = extract_to / Path(info.filename).name
                    with zf.open(info) as source, open(extracted_path, "wb") as target:
                        target.write(source.read())
                    
                    extracted_files.append(extracted_path)
                    logger.info(f"Extracted: {extracted_path.name}")
        
        except Exception as e:
            logger.error(f"Error extracting ZIP files: {e}")
            raise
        
        if not extracted_files:
            logger.warning(f"No supported files found in {file_path.name}")
        
        return extracted_files
    
    def list_files(
        self,
        file_path: Path,
        supported_only: bool = True,
    ) -> list[str]:
        """List files in ZIP archive.
        
        Args:
            file_path: Path to ZIP file
            supported_only: Only list supported file formats
            
        Returns:
            list[str]: List of file names in archive
            
        Example:
            >>> handler = ZIPHandler()
            >>> files = handler.list_files(Path("archive.zip"))
            >>> print(f"Archive contains {len(files)} files")
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                files = zf.namelist()
                
                if supported_only:
                    files = [
                        f for f in files
                        if Path(f).suffix.lower() in SUPPORTED_FORMATS
                    ]
                
                return files
        
        except Exception as e:
            logger.error(f"Error listing ZIP files: {e}")
            return []
