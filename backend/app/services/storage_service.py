"""
Supabase Storage Service

Handles file storage operations for transcriptions using Supabase Storage.
Transcription text is stored as gzip-compressed files to reduce size and costs.
"""

import os
import gzip
import logging
from pathlib import Path
from typing import Optional
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bucket name for transcription texts
TRANSCRIPTIONS_BUCKET = "transcriptions"


class StorageService:
    """Service for managing Supabase Storage operations."""

    def __init__(self):
        """Initialize Supabase client for storage operations."""
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the transcriptions bucket exists in Supabase Storage."""
        try:
            # List buckets to check if our bucket exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.get("name") or b.get("id") for b in buckets]

            if TRANSCRIPTIONS_BUCKET not in bucket_names:
                logger.info(f"Creating bucket: {TRANSCRIPTIONS_BUCKET}")
                # Create bucket if it doesn't exist
                self.supabase.storage.create_bucket(
                    id=TRANSCRIPTIONS_BUCKET,
                    options={
                        "public": False,  # Private bucket - requires auth
                        "file_size_limit": 104857600,  # 100MB max file size
                    }
                )
                logger.info(f"Bucket created: {TRANSCRIPTIONS_BUCKET}")
        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {e}")

    def save_transcription_text(
        self,
        transcription_id: str,
        text: str,
        compression_level: int = 6
    ) -> str:
        """
        Save transcription text to Supabase Storage as gzip-compressed file.

        Args:
            transcription_id: Transcription UUID
            text: Transcription text to save
            compression_level: Gzip compression level (1-9, default 6)

        Returns:
            str: Storage path (e.g., "{transcription_id}.txt.gz")

        Raises:
            Exception: If upload fails
        """
        try:
            # Compress text
            text_bytes = text.encode('utf-8')
            compressed_bytes = gzip.compress(text_bytes, compresslevel=compression_level)

            # Create storage path
            storage_path = f"{transcription_id}.txt.gz"

            # Upload to Supabase Storage
            logger.info(f"Uploading to storage: {storage_path} ({len(compressed_bytes)} bytes compressed)")

            self.supabase.storage.from_(TRANSCRIPTIONS_BUCKET).upload(
                file=compressed_bytes,
                path=storage_path,
                file_options={
                    "content-type": "application/gzip",
                    "upsert": "true"  # Overwrite if exists
                }
            )

            logger.info(f"Successfully uploaded to storage: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Failed to upload to storage: {e}")
            raise

    def get_transcription_text(self, transcription_id: str) -> str:
        """
        Download and decompress transcription text from Supabase Storage.

        Args:
            transcription_id: Transcription UUID

        Returns:
            str: Decompressed transcription text

        Raises:
            Exception: If download or decompression fails
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"

            logger.debug(f"Downloading from storage: {storage_path}")

            # Download from Supabase Storage
            response = self.supabase.storage.from_(TRANSCRIPTIONS_BUCKET).download(storage_path)

            # Decompress
            decompressed_bytes = gzip.decompress(response)
            text = decompressed_bytes.decode('utf-8')

            logger.debug(f"Downloaded and decompressed: {len(text)} chars from {storage_path}")
            return text

        except Exception as e:
            logger.error(f"Failed to download from storage: {e}")
            raise

    def delete_transcription_text(self, transcription_id: str) -> bool:
        """
        Delete transcription text from Supabase Storage.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"

            logger.info(f"Deleting from storage: {storage_path}")

            # Delete from Supabase Storage
            self.supabase.storage.from_(TRANSCRIPTIONS_BUCKET).remove([storage_path])

            logger.info(f"Deleted from storage: {storage_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete from storage (may not exist): {e}")
            return False

    def transcription_exists(self, transcription_id: str) -> bool:
        """
        Check if transcription text exists in Supabase Storage.

        Args:
            transcription_id: Transcription UUID

        Returns:
            bool: True if file exists
        """
        try:
            storage_path = f"{transcription_id}.txt.gz"
            # Try to get file info
            self.supabase.storage.from_(TRANSCRIPTIONS_BUCKET).get_metadata(storage_path)
            return True
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
