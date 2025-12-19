"""Secure file cleanup utilities.

Handles safe deletion of temporary files and directories.
Ensures user data privacy.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages safe cleanup of temporary files.
    
    Provides synchronous and asynchronous cleanup operations.
    Logs all cleanup actions for audit trail.
    """
    
    @staticmethod
    def cleanup_file(file_path: Path) -> bool:
        """Delete a single file securely.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if successful, False otherwise
            
        Example:
            >>> CleanupManager.cleanup_file(Path("/tmp/temp_file.txt"))
            True
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            else:
                logger.debug(f"File not found: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    @staticmethod
    def cleanup_directory(dir_path: Path) -> bool:
        """Delete a directory and all its contents.
        
        Args:
            dir_path: Path to directory to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                logger.info(f"Deleted directory: {dir_path}")
                return True
            else:
                logger.debug(f"Directory not found: {dir_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete directory {dir_path}: {e}")
            return False
    
    @staticmethod
    async def cleanup_file_async(file_path: Path) -> bool:
        """Delete a file asynchronously.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            CleanupManager.cleanup_file,
            file_path,
        )
    
    @staticmethod
    async def cleanup_directory_async(dir_path: Path) -> bool:
        """Delete a directory asynchronously.
        
        Args:
            dir_path: Path to directory to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            CleanupManager.cleanup_directory,
            dir_path,
        )
    
    @staticmethod
    def cleanup_files(
        file_paths: list[Path],
        ignore_errors: bool = True,
    ) -> int:
        """Delete multiple files.
        
        Args:
            file_paths: List of file paths
            ignore_errors: Continue even if some deletions fail
            
        Returns:
            int: Number of successfully deleted files
        """
        deleted_count = 0
        
        for file_path in file_paths:
            if CleanupManager.cleanup_file(file_path):
                deleted_count += 1
            elif not ignore_errors:
                break
        
        logger.info(f"Deleted {deleted_count}/{len(file_paths)} files")
        return deleted_count
    
    @staticmethod
    async def cleanup_files_async(
        file_paths: list[Path],
        ignore_errors: bool = True,
    ) -> int:
        """Delete multiple files asynchronously.
        
        Args:
            file_paths: List of file paths
            ignore_errors: Continue even if some deletions fail
            
        Returns:
            int: Number of successfully deleted files
        """
        tasks = [CleanupManager.cleanup_file_async(f) for f in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        deleted_count = sum(1 for r in results if r is True)
        logger.info(f"Deleted {deleted_count}/{len(file_paths)} files")
        return deleted_count
    
    @staticmethod
    def create_temp_directory(base_dir: Path, user_id: int) -> Path:
        """Create a secure temporary directory for a user.
        
        Uses user ID to create isolated directories.
        
        Args:
            base_dir: Base temporary directory
            user_id: Telegram user ID
            
        Returns:
            Path: Created directory path
            
        Raises:
            OSError: If directory cannot be created
        """
        temp_dir = base_dir / str(user_id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temp directory: {temp_dir}")
        return temp_dir
