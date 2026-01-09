"""
Storage Service Error Handling Tests

Tests error handling and edge cases for the storage service.
"""

import pytest
import gzip
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from app.services.storage_service import get_storage_service


@pytest.fixture
def storage_service(tmp_path):
    """Create a storage service with temp directory."""
    # Set environment variable for test path
    original_path = os.environ.get('TRANSCRIBE_PATH')
    os.environ['TRANSCRIBE_PATH'] = str(tmp_path)

    # Reload the storage service module to use new path
    import importlib
    from app.services import storage_service
    importlib.reload(storage_service)

    service = storage_service.get_storage_service()

    yield service

    # Restore original path
    if original_path:
        os.environ['TRANSCRIBE_PATH'] = original_path
    elif 'TRANSCRIBE_PATH' in os.environ:
        del os.environ['TRANSCRIBE_PATH']


class TestStorageServiceErrors:
    """Test error handling in storage service."""

    def test_save_transcription_text_with_empty_string(self, storage_service):
        """Test saving empty string content."""
        transcription_id = "test-uuid-123"

        # Empty string should be allowed (represents empty transcription)
        storage_service.save_transcription_text(transcription_id, "")

        # Should be able to retrieve it
        result = storage_service.get_transcription_text(transcription_id)
        assert result == ""

    def test_get_transcription_text_nonexistent_file(self, storage_service):
        """Test getting text from non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_transcription_text("nonexistent-uuid")

    def test_delete_transcription_text_nonexistent(self, storage_service):
        """Test deleting non-existent file doesn't raise error."""
        # Should not raise an error for non-existent file
        storage_service.delete_transcription_text("nonexistent-uuid")

        # No exception means success
        assert True

    def test_save_transcription_text_with_unicode(self, storage_service):
        """Test saving and retrieving text with unicode characters."""
        transcription_id = "unicode-test"

        # Text with various unicode characters
        unicode_text = "Hello 世界 🎉 Привет mundo"

        storage_service.save_transcription_text(transcription_id, unicode_text)
        result = storage_service.get_transcription_text(transcription_id)

        assert result == unicode_text

    def test_save_transcription_text_very_long_content(self, storage_service):
        """Test handling very long text content."""
        transcription_id = "long-content"

        # Create a very long string (1MB+)
        long_text = "A" * (1024 * 1024 + 1000)

        storage_service.save_transcription_text(transcription_id, long_text)
        result = storage_service.get_transcription_text(transcription_id)

        assert len(result) == len(long_text)
        assert result == long_text

    def test_save_transcription_text_with_special_characters(self, storage_service):
        """Test saving text with special characters."""
        transcription_id = "special-chars"

        special_text = "Test\n\t\r with \"quotes\" and 'apostrophes'"

        storage_service.save_transcription_text(transcription_id, special_text)
        result = storage_service.get_transcription_text(transcription_id)

        assert result == special_text

    def test_file_path_within_base_directory(self, storage_service, tmp_path):
        """Test that file paths are within base directory."""
        from app.services.storage_service import TRANSCRIPTIONS_DIR

        # Use a valid UUID format
        test_id = "550e8400-e29b-41d4-a716-446655440000"

        # Save a file
        storage_service.save_transcription_text(test_id, "test content")

        # File should exist at the expected path
        expected_path = TRANSCRIPTIONS_DIR / f"{test_id}.txt.gz"
        assert expected_path.exists()

        # Clean up
        storage_service.delete_transcription_text(test_id)

    def test_compression_ratio(self, storage_service):
        """Test that gzip compression actually reduces file size."""
        from app.services.storage_service import TRANSCRIPTIONS_DIR

        transcription_id = "compression-test"

        # Create repetitive content that compresses well
        repetitive_text = "The quick brown fox jumps over the lazy dog. " * 1000

        storage_service.save_transcription_text(transcription_id, repetitive_text)

        # Check file size
        file_path = TRANSCRIPTIONS_DIR / f"{transcription_id}.txt.gz"
        compressed_size = file_path.stat().st_size
        original_size = len(repetitive_text.encode('utf-8'))

        # Compressed should be significantly smaller
        assert compressed_size < original_size * 0.3  # At least 70% compression

        # Clean up
        storage_service.delete_transcription_text(transcription_id)
