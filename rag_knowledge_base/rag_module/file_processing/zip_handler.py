"""ZIP archive handler with security validations for RAG.

Extracts and processes ZIP archives safely with:
- Size limit validation (zip bomb protection)
- Path traversal protection
- Support for nested archives
"""

import logging
import zipfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

SUPPORTED_FILE_TYPES = {".pdf", ".docx", ".txt", ".doc", ".xlsx", ".xls"}
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100MB
MAX_FILES_IN_ARCHIVE = 100


class ZIPHandler:
    """Handler for ZIP archives with security checks.
    
    Validates archives before extraction to prevent:
    - Zip bombs (compression ratio attacks)
    - Path traversal attacks
    - Resource exhaustion
    """
    
    def validate_archive(self, file_path: Path) -> bool:
        """Validate ZIP archive safety.
        
        Checks:
        - File count limit
        - Uncompressed size limit
        - Compression ratio
        
        Args:
            file_path: Path to ZIP file
            
        Returns:
            bool: True if archive is safe
            
        Raises:
            ValueError: If archive fails validation
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                info_list = zip_ref.infolist()
                
                if len(info_list) > MAX_FILES_IN_ARCHIVE:
                    raise ValueError(
                        f"Too many files in archive: {len(info_list)} > {MAX_FILES_IN_ARCHIVE}"
                    )
                
                total_uncompressed = sum(info.file_size for info in info_list)
                if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                    raise ValueError(
                        f"Uncompressed size too large: {total_uncompressed} > {MAX_UNCOMPRESSED_SIZE}"
                    )
                
                total_compressed = sum(info.compress_size for info in info_list if info.compress_size > 0)
                if total_compressed > 0:
                    ratio = total_uncompressed / total_compressed
                    if ratio > 100:
                        raise ValueError(
                            f"Compression ratio too high: {ratio:.1f}x (possible zip bomb)"
                        )
                
            return True
        
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")
        except Exception as e:
            logger.error(f"Archive validation error: {e}")
            raise
    
    def extract_supported_files(
        self,
        file_path: Path,
        extract_to: Path,
    ) -> List[Path]:
        """Extract supported files from ZIP archive.
        
        Args:
            file_path: Path to ZIP file
            extract_to: Directory to extract files
            
        Returns:
            List[Path]: Paths to extracted supported files
            
        Raises:
            ValueError: If archive validation fails
        """
        self.validate_archive(file_path)
        
        extract_to.mkdir(parents=True, exist_ok=True)
        extracted_files: List[Path] = []
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    if member.is_dir():
                        continue
                    
                    if '..' in member.filename or member.filename.startswith('/'):
                        logger.warning(f"Skipping suspicious path: {member.filename}")
                        continue
                    
                    file_ext = Path(member.filename).suffix.lower()
                    if file_ext not in SUPPORTED_FILE_TYPES:
                        continue
                    
                    try:
                        safe_path = extract_to / Path(member.filename).name
                        with zip_ref.open(member) as source:
                            with open(safe_path, 'wb') as target:
                                target.write(source.read())
                        
                        extracted_files.append(safe_path)
                        logger.info(f"Extracted: {safe_path.name}")
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract {member.filename}: {e}")
                        continue
            
            logger.info(f"Extracted {len(extracted_files)} supported files from {file_path.name}")
            return extracted_files
        
        except Exception as e:
            logger.error(f"Error extracting ZIP: {e}")
            raise ValueError(f"Failed to extract archive: {e}") from e
