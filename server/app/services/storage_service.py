"""
Local File Storage Service

Handles file storage operations for transcriptions using local filesystem.
Transcription text is stored as gzip-compressed files to reduce size.
Segments and original output are also saved for proper SRT generation and debugging.
"""

import os
import gzip
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

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

    # ========================================================================
    # Segment Storage (for proper SRT subtitles)
    # ========================================================================

    def save_transcription_segments(
        self,
        transcription_id: str,
        segments: List[Dict[str, Any]],
        compression_level: int = 6
    ) -> str:
        """
        Save transcription segments with timestamps to gzip-compressed JSON file.

        Args:
            transcription_id: Transcription UUID
            segments: List of segment dicts with start, end, text
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Relative storage path (e.g., "{transcription_id}.segments.json.gz")

        Raises:
            Exception: If save fails
        """
        try:
            # Convert to JSON and compress
            json_str = json.dumps(segments, ensure_ascii=False)
            compressed_bytes = gzip.compress(
                json_str.encode('utf-8'),
                compresslevel=compression_level
            )

            # Create storage path
            storage_path = f"{transcription_id}.segments.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            # Write to local filesystem
            logger.info(
                f"Saving segments: {storage_path} "
                f"({len(segments)} segments, {len(compressed_bytes)} bytes compressed)"
            )
            file_path.write_bytes(compressed_bytes)
            logger.info(f"Successfully saved segments: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to save segments: {e}")
            raise

    def get_transcription_segments(self, transcription_id: str) -> List[Dict[str, Any]]:
        """
        Read and decompress transcription segments from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            List[Dict]: List of segment dicts with start, end, text
            Returns empty list if file doesn't exist

        Raises:
            Exception: If read or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.segments.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.debug(f"Reading segments from local storage: {storage_path}")

            # Read and decompress
            compressed_bytes = file_path.read_bytes()
            decompressed_bytes = gzip.decompress(compressed_bytes)
            segments = json.loads(decompressed_bytes.decode('utf-8'))

            logger.debug(f"Read {len(segments)} segments from {storage_path}")
            return segments

        except FileNotFoundError:
            logger.debug(f"Segments file not found: {storage_path}")
            return []
        except Exception as e:
            logger.error(f"Failed to read segments: {e}")
            raise

    def delete_transcription_segments(self, transcription_id: str) -> bool:
        """
        Delete transcription segments from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.segments.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path
            file_path.unlink()
            logger.info(f"Deleted segments: {storage_path}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Failed to delete segments: {e}")
            return False

    def segments_exist(self, transcription_id: str) -> bool:
        """
        Check if transcription segments exist in local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if segments file exists
        """
        try:
            storage_path = f"{transcription_id}.segments.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path
            return file_path.exists()
        except Exception:
            return False

    # ========================================================================
    # Original Output Storage (for debugging)
    # ========================================================================

    def save_original_output(
        self,
        transcription_id: str,
        original: Dict[str, Any],
        compression_level: int = 6
    ) -> str:
        """
        Save original faster-whisper output to gzip-compressed JSON file.

        Args:
            transcription_id: Transcription UUID
            original: Full faster-whisper output dict
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Relative storage path (e.g., "{transcription_id}.original.json.gz")

        Raises:
            Exception: If save fails
        """
        try:
            # Convert to JSON with default=str for non-serializable types
            json_str = json.dumps(original, ensure_ascii=False, default=str)
            compressed_bytes = gzip.compress(
                json_str.encode('utf-8'),
                compresslevel=compression_level
            )

            # Create storage path
            storage_path = f"{transcription_id}.original.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            # Write to local filesystem
            logger.info(
                f"Saving original output: {storage_path} "
                f"({len(compressed_bytes)} bytes compressed)"
            )
            file_path.write_bytes(compressed_bytes)
            logger.info(f"Successfully saved original output: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to save original output: {e}")
            raise

    def get_original_output(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """
        Read and decompress original faster-whisper output from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            Optional[Dict]: Original output dict, or None if not found

        Raises:
            Exception: If read or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.original.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.debug(f"Reading original output from local storage: {storage_path}")

            # Read and decompress
            compressed_bytes = file_path.read_bytes()
            decompressed_bytes = gzip.decompress(compressed_bytes)
            original = json.loads(decompressed_bytes.decode('utf-8'))

            logger.debug(f"Read original output from {storage_path}")
            return original

        except FileNotFoundError:
            logger.debug(f"Original output file not found: {storage_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to read original output: {e}")
            raise

    def delete_original_output(self, transcription_id: str) -> bool:
        """
        Delete original faster-whisper output from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.original.json.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path
            file_path.unlink()
            logger.info(f"Deleted original output: {storage_path}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Failed to delete original output: {e}")
            return False

    # ========================================================================
    # Formatted Text Storage (LLM-formatted transcription)
    # ========================================================================

    def save_formatted_text(
        self,
        transcription_id: str,
        text: str,
        compression_level: int = 6
    ) -> str:
        """
        Save LLM-formatted transcription text to gzip-compressed file.

        Args:
            transcription_id: Transcription UUID
            text: Formatted transcription text to save
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Relative storage path (e.g., "{transcription_id}.formatted.txt.gz")

        Raises:
            Exception: If save fails
        """
        try:
            # Compress text
            text_bytes = text.encode('utf-8')
            compressed_bytes = gzip.compress(text_bytes, compresslevel=compression_level)

            # Create storage path
            storage_path = f"{transcription_id}.formatted.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            # Write to local filesystem
            logger.info(f"Saving formatted text: {storage_path} ({len(compressed_bytes)} bytes compressed)")
            file_path.write_bytes(compressed_bytes)
            logger.info(f"Successfully saved formatted text: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to save formatted text: {e}")
            raise

    def get_formatted_text(self, transcription_id: str) -> str:
        """
        Read and decompress formatted transcription text from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            str: Decompressed formatted transcription text

        Raises:
            Exception: If read or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.formatted.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.debug(f"Reading formatted text from local storage: {storage_path}")

            # Read from local filesystem
            compressed_bytes = file_path.read_bytes()

            # Decompress
            decompressed_bytes = gzip.decompress(compressed_bytes)
            text = decompressed_bytes.decode('utf-8')

            logger.debug(f"Read formatted text: {len(text)} chars from {storage_path}")
            return text

        except FileNotFoundError:
            logger.error(f"Formatted text file not found: {storage_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read formatted text: {e}")
            raise

    def delete_formatted_text(self, transcription_id: str) -> bool:
        """
        Delete formatted transcription text from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.formatted.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.info(f"Deleting formatted text: {storage_path}")

            # Delete from local filesystem
            file_path.unlink()
            logger.info(f"Deleted formatted text: {storage_path}")
            return True

        except FileNotFoundError:
            logger.warning(f"Formatted text file not found (may not exist): {storage_path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete formatted text: {e}")
            return False

    def formatted_text_exists(self, transcription_id: str) -> bool:
        """
        Check if formatted transcription text exists in local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if formatted text file exists
        """
        try:
            storage_path = f"{transcription_id}.formatted.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path
            return file_path.exists()
        except Exception:
            return False

    # ========================================================================
    # NotebookLM Guideline Storage
    # ========================================================================

    def save_notebooklm_guideline(
        self,
        transcription_id: str,
        text: str,
        compression_level: int = 6
    ) -> str:
        """
        Save NotebookLM guideline text to gzip-compressed file.

        Args:
            transcription_id: Transcription UUID
            text: Guideline text to save
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Relative storage path (e.g., "{transcription_id}.notebooklm.txt.gz")

        Raises:
            Exception: If save fails
        """
        try:
            # Compress text
            text_bytes = text.encode('utf-8')
            compressed_bytes = gzip.compress(text_bytes, compresslevel=compression_level)

            # Create storage path
            storage_path = f"{transcription_id}.notebooklm.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            # Write to local filesystem
            logger.info(f"Saving NotebookLM guideline: {storage_path} ({len(compressed_bytes)} bytes compressed)")
            file_path.write_bytes(compressed_bytes)
            logger.info(f"Successfully saved NotebookLM guideline: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to save NotebookLM guideline: {e}")
            raise

    def get_notebooklm_guideline(self, transcription_id: str) -> str:
        """
        Read and decompress NotebookLM guideline from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            str: Decompressed guideline text

        Raises:
            Exception: If read or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.notebooklm.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.debug(f"Reading NotebookLM guideline from local storage: {storage_path}")

            # Read from local filesystem
            compressed_bytes = file_path.read_bytes()

            # Decompress
            decompressed_bytes = gzip.decompress(compressed_bytes)
            text = decompressed_bytes.decode('utf-8')

            logger.debug(f"Read NotebookLM guideline: {len(text)} chars from {storage_path}")
            return text

        except FileNotFoundError:
            logger.error(f"NotebookLM guideline file not found: {storage_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read NotebookLM guideline: {e}")
            raise

    def delete_notebooklm_guideline(self, transcription_id: str) -> bool:
        """
        Delete NotebookLM guideline from local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.notebooklm.txt.gz"
            file_path = TRANSCRIPTIONS_DIR / storage_path

            logger.info(f"Deleting NotebookLM guideline: {storage_path}")

            # Delete from local filesystem
            file_path.unlink()
            logger.info(f"Deleted NotebookLM guideline: {storage_path}")
            return True

        except FileNotFoundError:
            logger.warning(f"NotebookLM guideline file not found (may not exist): {storage_path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete NotebookLM guideline: {e}")
            return False

    def notebooklm_guideline_exists(self, transcription_id: str) -> bool:
        """
        Check if NotebookLM guideline exists in local filesystem.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if guideline file exists
        """
        try:
            storage_path = f"{transcription_id}.notebooklm.txt.gz"
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
