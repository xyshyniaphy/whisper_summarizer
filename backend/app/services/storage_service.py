"""
Local File Storage Service

Handles file storage operations for transcriptions using local filesystem.
Transcription text is stored as gzip-compressed files to reduce size.
"""

import os
import gzip
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Local storage directory for transcription texts
TRANSCRIPTIONS_DIR = Path("/app/data/transcribes")


class StorageService:
    """Service for managing local file storage operations."""

    def __init__(self):
        """Initialize local storage directory."""
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Ensure the transcriptions directory exists."""
        try:
            TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directory ready: {TRANSCRIPTIONS_DIR}")
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise

    def save_transcription_text(
        self,
        transcription_id: str,
        text: str,
        compression_level: int = 6
    ) -> str:
        """
        Save transcription text to local filesystem as gzip-compressed file.

        Args:
            transcription_id: Transcription UUID
            text: Transcription text to save
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Relative storage path (e.g., "{transcription_id}.txt.gz")

        Raises:
            Exception: If save fails
        """
        try:
            # Compress text
            text_bytes = text.encode('utf-8')
            compressed_bytes = gzip.compress(text_bytes, compresslevel=compression_level)

            # Create storage path
            storage_path = f"{transcription_id}.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            # Write to local filesystem
            logger.info(f"Saving to local storage: {storage_path} ({len(compressed_bytes)} bytes compressed)")
            file_path.write_bytes(compressed_bytes)
            logger.info(f"Successfully saved to local storage: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to save to local storage: {e}")
            raise

    def get_transcription_text(self, transcription_id: str) -> str:
        """
        Read and decompress transcription text from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            str: Decompressed transcription text

        Raises:
            Exception: If read or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.debug(f"Reading from local storage: {storage_path}")

            # Read from local filesystem
            compressed_bytes = file_path.read_bytes()

            # Decompress
            decompressed_bytes = gzip.decompress(compressed_bytes)
            text = decompressed_bytes.decode('utf-8')

            logger.debug(f"Read and decompressed: {len(text)} chars from {storage_path}")
            return text

        except FileNotFoundError:
            logger.error(f"File not found in local storage: {storage_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read from local storage: {e}")
            raise

    def delete_transcription_text(self, transcription_id: str) -> bool:
        """
        Delete transcription text from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.info(f"Deleting from local storage: {storage_path}")

            # Delete from local filesystem
            file_path.unlink()
            logger.info(f"Deleted from local storage: {storage_path}")
            return True

        except FileNotFoundError:
            logger.warning(f"File not found in local storage (may not exist): {storage_path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete from local storage: {e}")
            return False

    def transcription_exists(self, transcription_id: str) -> bool:
        """
        Check if transcription text exists in local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if file exists
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path
            return file_path.exists()
        except Exception:
            return False


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the singleton StorageService instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
        logger.info("StorageService initialized")
    return _storage_service
