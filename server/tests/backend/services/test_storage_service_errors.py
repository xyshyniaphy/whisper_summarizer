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
from app.services.storage_service import get_storage_service, StorageService


@pytest.fixture
def storage_service(tmp_path):
    """Create a storage service with temp directory."""
    # Set environment variable for test path
    original_path = os.environ.get('TRANSCRIBE_PATH')
    os.environ['TRANSCRIBE_PATH'] = str(tmp_path)

    # Reload the storage service module to use new path
    import importlib
    from app.services import storage_service as ss_module
    importlib.reload(ss_module)

    # Reset singleton
    ss_module._storage_service = None
    service = ss_module.get_storage_service()

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


# ============================================================================
# Segments Storage Tests
# ============================================================================

class TestSegmentsStorage:
    """Test segments storage functionality."""

    def test_save_and_get_segments(self, storage_service):
        """Test saving and retrieving segments."""
        transcription_id = "segments-test"

        segments = [
            {"start": "00:00:00,000", "end": "00:00:05,000", "text": "First segment"},
            {"start": "00:00:05,000", "end": "00:00:10,000", "text": "Second segment"},
        ]

        storage_service.save_transcription_segments(transcription_id, segments)
        result = storage_service.get_transcription_segments(transcription_id)

        assert result == segments

    def test_get_segments_nonexistent_returns_empty(self, storage_service):
        """Test getting segments from non-existent file returns empty list."""
        result = storage_service.get_transcription_segments("nonexistent-uuid")
        assert result == []

    def test_delete_segments(self, storage_service):
        """Test deleting segments."""
        transcription_id = "delete-segments"
        segments = [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "Text"}]

        storage_service.save_transcription_segments(transcription_id, segments)
        assert storage_service.segments_exist(transcription_id)

        result = storage_service.delete_transcription_segments(transcription_id)
        assert result is True
        assert not storage_service.segments_exist(transcription_id)

    def test_delete_segments_nonexistent(self, storage_service):
        """Test deleting non-existent segments returns False."""
        result = storage_service.delete_transcription_segments("nonexistent-uuid")
        assert result is False

    def test_segments_exist(self, storage_service):
        """Test checking if segments exist."""
        import uuid
        transcription_id = f"exist-segments-{uuid.uuid4()}"
        segments = [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "Text"}]

        assert not storage_service.segments_exist(transcription_id)

        storage_service.save_transcription_segments(transcription_id, segments)
        assert storage_service.segments_exist(transcription_id)

    def test_segments_with_unicode(self, storage_service):
        """Test segments with unicode content."""
        transcription_id = "unicode-segments"
        segments = [
            {"start": "00:00:00,000", "end": "00:00:05,000", "text": "中文 🎵 日本語"}
        ]

        storage_service.save_transcription_segments(transcription_id, segments)
        result = storage_service.get_transcription_segments(transcription_id)

        assert result[0]["text"] == "中文 🎵 日本語"


# ============================================================================
# Original Output Storage Tests
# ============================================================================

class TestOriginalOutputStorage:
    """Test original output storage functionality."""

    def test_save_and_get_original_output(self, storage_service):
        """Test saving and retrieving original output."""
        transcription_id = "original-test"

        original = {
            "text": "Transcription text",
            "segments": [{"start": 0, "end": 5, "text": "Segment"}],
            "language": "zh"
        }

        storage_service.save_original_output(transcription_id, original)
        result = storage_service.get_original_output(transcription_id)

        assert result["text"] == "Transcription text"
        assert result["language"] == "zh"

    def test_get_original_nonexistent_returns_none(self, storage_service):
        """Test getting original output from non-existent file returns None."""
        result = storage_service.get_original_output("nonexistent-uuid")
        assert result is None

    def test_delete_original_output(self, storage_service):
        """Test deleting original output."""
        transcription_id = "delete-original"
        original = {"text": "Text"}

        storage_service.save_original_output(transcription_id, original)
        assert storage_service.delete_original_output(transcription_id) is True

    def test_delete_original_nonexistent(self, storage_service):
        """Test deleting non-existent original output returns False."""
        result = storage_service.delete_original_output("nonexistent-uuid")
        assert result is False

    def test_original_with_complex_types(self, storage_service):
        """Test saving original output with complex types."""
        transcription_id = "complex-original"

        original = {
            "text": "Text",
            "float_value": 123.456,
            "int_value": 42,
            "bool_value": True,
            "none_value": None,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"}
        }

        storage_service.save_original_output(transcription_id, original)
        result = storage_service.get_original_output(transcription_id)

        assert result["float_value"] == 123.456
        assert result["bool_value"] is True
        assert result["none_value"] is None
        assert result["list_value"] == [1, 2, 3]


# ============================================================================
# Formatted Text Storage Tests
# ============================================================================

class TestFormattedTextStorage:
    """Test formatted text storage functionality."""

    def test_save_and_get_formatted_text(self, storage_service):
        """Test saving and retrieving formatted text."""
        transcription_id = "formatted-test"

        formatted = "This is formatted text with proper punctuation."

        storage_service.save_formatted_text(transcription_id, formatted)
        result = storage_service.get_formatted_text(transcription_id)

        assert result == formatted

    def test_get_formatted_nonexistent_raises_error(self, storage_service):
        """Test getting formatted text from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_formatted_text("nonexistent-uuid")

    def test_delete_formatted_text(self, storage_service):
        """Test deleting formatted text."""
        transcription_id = "delete-formatted"

        storage_service.save_formatted_text(transcription_id, "Text")
        assert storage_service.delete_formatted_text(transcription_id) is True
        assert storage_service.delete_formatted_text(transcription_id) is False

    def test_formatted_text_exists(self, storage_service):
        """Test checking if formatted text exists."""
        import uuid
        transcription_id = f"exist-formatted-{uuid.uuid4()}"

        assert not storage_service.formatted_text_exists(transcription_id)

        storage_service.save_formatted_text(transcription_id, "Text")
        assert storage_service.formatted_text_exists(transcription_id)


# ============================================================================
# NotebookLM Guideline Storage Tests
# ============================================================================

class TestNotebookLMStorage:
    """Test NotebookLM guideline storage functionality."""

    def test_save_and_get_notebooklm_guideline(self, storage_service):
        """Test saving and retrieving NotebookLM guideline."""
        transcription_id = "notebooklm-test"

        guideline = "## 概述\n\nThis is the guideline content."

        storage_service.save_notebooklm_guideline(transcription_id, guideline)
        result = storage_service.get_notebooklm_guideline(transcription_id)

        assert result == guideline

    def test_get_notebooklm_nonexistent_raises_error(self, storage_service):
        """Test getting guideline from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_notebooklm_guideline("nonexistent-uuid")

    def test_delete_notebooklm_guideline(self, storage_service):
        """Test deleting NotebookLM guideline."""
        transcription_id = "delete-notebooklm"

        storage_service.save_notebooklm_guideline(transcription_id, "Guideline")
        assert storage_service.delete_notebooklm_guideline(transcription_id) is True
        assert storage_service.delete_notebooklm_guideline(transcription_id) is False

    def test_notebooklm_guideline_exists(self, storage_service):
        """Test checking if guideline exists."""
        import uuid
        transcription_id = f"exist-notebooklm-{uuid.uuid4()}"

        assert not storage_service.notebooklm_guideline_exists(transcription_id)

        storage_service.save_notebooklm_guideline(transcription_id, "Guideline")
        assert storage_service.notebooklm_guideline_exists(transcription_id)

    def test_notebooklm_with_markdown(self, storage_service):
        """Test guideline with markdown content."""
        transcription_id = "markdown-notebooklm"

        guideline = """
# Title

## Section 1

- Item 1
- Item 2

**Bold** and *italic* text.
"""

        storage_service.save_notebooklm_guideline(transcription_id, guideline)
        result = storage_service.get_notebooklm_guideline(transcription_id)

        assert "**Bold**" in result
        assert "*italic*" in result


# ============================================================================
# Initialization Tests
# ============================================================================

class TestStorageServiceInit:
    """Test storage service initialization."""

    def test_creates_directory_on_init(self, tmp_path):
        """Test that directory is created on initialization."""
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', tmp_path / "new_dir"):
            service = StorageService()

        assert (tmp_path / "new_dir").exists()

    def test_singleton_pattern(self, tmp_path):
        """Test that get_storage_service returns singleton."""
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', tmp_path):
            service1 = get_storage_service()
            service2 = get_storage_service()

        assert service1 is service2


# ============================================================================
# Compression Level Tests
# ============================================================================

class TestCompressionLevels:
    """Test different compression levels."""

    def test_different_compression_levels(self, storage_service):
        """Test saving with different compression levels."""
        transcription_id_1 = "compress-1"
        transcription_id_9 = "compress-9"

        text = "A" * 10000  # Repetitive content

        storage_service.save_transcription_text(transcription_id_1, text, compression_level=1)
        storage_service.save_transcription_text(transcription_id_9, text, compression_level=9)

        # Level 9 should be smaller than level 1
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        size_1 = (TRANSCRIPTIONS_DIR / f"{transcription_id_1}.txt.gz").stat().st_size
        size_9 = (TRANSCRIPTIONS_DIR / f"{transcription_id_9}.txt.gz").stat().st_size

        assert size_9 < size_1

    def test_invalid_compression_level(self, storage_service):
        """Test that invalid compression levels are handled by gzip."""
        # Gzip will raise error for invalid compression levels
        transcription_id = "invalid-compress"

        # This should raise an error for invalid compression level
        with pytest.raises(Exception):  # zlib.error
            storage_service.save_transcription_text(transcription_id, "text", compression_level=100)


# ============================================================================
# Edge Cases
# ============================================================================

class TestStorageServiceEdgeCases:
    """Test edge cases for storage service."""

    def test_multiple_saves_overwrite(self, storage_service):
        """Test that multiple saves overwrite previous data."""
        transcription_id = "overwrite-test"

        storage_service.save_transcription_text(transcription_id, "First version")
        storage_service.save_transcription_text(transcription_id, "Second version")

        result = storage_service.get_transcription_text(transcription_id)
        assert result == "Second version"

    def test_concurrent_access(self, storage_service):
        """Test that concurrent access is handled."""
        transcription_id = "concurrent-test"

        # Save multiple times
        for i in range(10):
            storage_service.save_transcription_text(f"{transcription_id}-{i}", f"Text {i}")

        # All should be retrievable
        for i in range(10):
            result = storage_service.get_transcription_text(f"{transcription_id}-{i}")
            assert result == f"Text {i}"

    def test_special_characters_in_segments(self, storage_service):
        """Test segments with special characters."""
        transcription_id = "special-segments"

        segments = [
            {
                "start": "00:00:00,000",
                "end": "00:00:05,000",
                "text": "Text with \"quotes\" and 'apostrophes' and\nnewlines"
            }
        ]

        storage_service.save_transcription_segments(transcription_id, segments)
        result = storage_service.get_transcription_segments(transcription_id)

        assert "\"quotes\"" in result[0]["text"]
        assert "'apostrophes'" in result[0]["text"]

    def test_empty_segments_list(self, storage_service):
        """Test saving and retrieving empty segments list."""
        transcription_id = "empty-segments"

        storage_service.save_transcription_segments(transcription_id, [])
        result = storage_service.get_transcription_segments(transcription_id)

        assert result == []

    def test_very_long_segments_list(self, storage_service):
        """Test saving many segments."""
        transcription_id = "many-segments"

        segments = [
            {"start": f"00:00:{i:02d},000", "end": f"00:00:{i+1:02d},000", "text": f"Segment {i}"}
            for i in range(1000)
        ]

        storage_service.save_transcription_segments(transcription_id, segments)
        result = storage_service.get_transcription_segments(transcription_id)

        assert len(result) == 1000
        assert result[999]["text"] == "Segment 999"


# ============================================================================
# Error Handling Tests (Covering Exception Paths)
# ============================================================================

class TestStorageServiceErrorHandling:
    """Test error handling and exception paths."""

    def test_should_fail_to_create_directory(self, tmp_path):
        """Should handle directory creation failure."""
        # Patch TRANSCRIPTIONS_DIR to a path that will fail
        invalid_path = tmp_path / "nonexistent" / "deep" / "path"
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', invalid_path):
            with patch.object(Path, 'mkdir', side_effect=PermissionError("Access denied")):
                with pytest.raises(PermissionError):
                    from app.services.storage_service import StorageService
                    StorageService()

    def test_should_handle_generic_read_exception(self, storage_service):
        """Should handle generic exception when reading transcription."""
        transcription_id = "read-error-test"

        # Create a file first
        storage_service.save_transcription_text(transcription_id, "test content")

        # Mock read_bytes to raise generic exception
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        file_path = TRANSCRIPTIONS_DIR / f"{transcription_id}.txt.gz"

        with patch.object(Path, 'read_bytes', side_effect=RuntimeError("Read failed")):
            with pytest.raises(RuntimeError, match="Read failed"):
                storage_service.get_transcription_text(transcription_id)

    def test_should_handle_generic_delete_exception(self, storage_service):
        """Should handle generic exception when deleting transcription."""
        transcription_id = "delete-error-test"

        # Create a file first
        storage_service.save_transcription_text(transcription_id, "test content")

        # Mock unlink to raise generic exception
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        file_path = TRANSCRIPTIONS_DIR / f"{transcription_id}.txt.gz"

        with patch.object(Path, 'unlink', side_effect=RuntimeError("Delete failed")):
            result = storage_service.delete_transcription_text(transcription_id)
            assert result is False

    def test_should_handle_exists_exception(self, storage_service):
        """Should handle exception in transcription_exists."""
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        file_path = TRANSCRIPTIONS_DIR / "test.txt.gz"

        with patch.object(Path, 'exists', side_effect=RuntimeError("Check failed")):
            result = storage_service.transcription_exists("test-id")
            assert result is False

    def test_should_handle_generic_segments_save_exception(self, storage_service):
        """Should handle generic exception when saving segments."""
        # Mock write_bytes to raise exception
        with patch.object(Path, 'write_bytes', side_effect=RuntimeError("Write failed")):
            with pytest.raises(RuntimeError, match="Write failed"):
                storage_service.save_transcription_segments("error-segments", [{"start": "00:00:00,000", "end": "00:00:01,000", "text": "Test"}])

    def test_should_handle_generic_segments_read_exception(self, storage_service):
        """Should handle generic exception when reading segments."""
        transcription_id = "segments-read-error"

        # Create segments file first
        segments = [{"start": "00:00:00,000", "end": "00:00:01,000", "text": "Test"}]
        storage_service.save_transcription_segments(transcription_id, segments)

        # Mock read_bytes to raise exception
        with patch.object(Path, 'read_bytes', side_effect=RuntimeError("Read failed")):
            with pytest.raises(RuntimeError, match="Read failed"):
                storage_service.get_transcription_segments(transcription_id)

    def test_should_handle_generic_segments_delete_exception(self, storage_service):
        """Should handle generic exception when deleting segments."""
        transcription_id = "segments-delete-error"

        # Create segments file first
        segments = [{"start": "00:00:00,000", "end": "00:00:01,000", "text": "Test"}]
        storage_service.save_transcription_segments(transcription_id, segments)

        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=RuntimeError("Delete failed")):
            result = storage_service.delete_transcription_segments(transcription_id)
            assert result is False

    def test_should_handle_segments_exists_exception(self, storage_service):
        """Should handle exception in segments_exist."""
        with patch.object(Path, 'exists', side_effect=RuntimeError("Check failed")):
            result = storage_service.segments_exist("test-id")
            assert result is False

    def test_should_handle_generic_original_save_exception(self, storage_service):
        """Should handle generic exception when saving original output."""
        with patch.object(Path, 'write_bytes', side_effect=RuntimeError("Write failed")):
            with pytest.raises(RuntimeError, match="Write failed"):
                storage_service.save_original_output("error-original", {"text": "Test"})

    def test_should_handle_generic_original_read_exception(self, storage_service):
        """Should handle generic exception when reading original output."""
        transcription_id = "original-read-error"

        # Create original output file first
        storage_service.save_original_output(transcription_id, {"text": "Test"})

        # Mock read_bytes to raise exception
        with patch.object(Path, 'read_bytes', side_effect=RuntimeError("Read failed")):
            with pytest.raises(RuntimeError, match="Read failed"):
                storage_service.get_original_output(transcription_id)

    def test_should_handle_generic_original_delete_exception(self, storage_service):
        """Should handle generic exception when deleting original output."""
        transcription_id = "original-delete-error"

        # Create original output file first
        storage_service.save_original_output(transcription_id, {"text": "Test"})

        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=RuntimeError("Delete failed")):
            result = storage_service.delete_original_output(transcription_id)
            assert result is False

    def test_should_handle_generic_formatted_save_exception(self, storage_service):
        """Should handle generic exception when saving formatted text."""
        with patch.object(Path, 'write_bytes', side_effect=RuntimeError("Write failed")):
            with pytest.raises(RuntimeError, match="Write failed"):
                storage_service.save_formatted_text("error-formatted", "Formatted text")

    def test_should_handle_generic_formatted_read_exception(self, storage_service):
        """Should handle generic exception when reading formatted text."""
        transcription_id = "formatted-read-error"

        # Create formatted text file first
        storage_service.save_formatted_text(transcription_id, "Formatted text")

        # Mock read_bytes to raise exception
        with patch.object(Path, 'read_bytes', side_effect=RuntimeError("Read failed")):
            with pytest.raises(RuntimeError, match="Read failed"):
                storage_service.get_formatted_text(transcription_id)

    def test_should_handle_generic_formatted_delete_exception(self, storage_service):
        """Should handle generic exception when deleting formatted text."""
        transcription_id = "formatted-delete-error"

        # Create formatted text file first
        storage_service.save_formatted_text(transcription_id, "Formatted text")

        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=RuntimeError("Delete failed")):
            result = storage_service.delete_formatted_text(transcription_id)
            assert result is False

    def test_should_handle_formatted_exists_exception(self, storage_service):
        """Should handle exception in formatted_text_exists."""
        with patch.object(Path, 'exists', side_effect=RuntimeError("Check failed")):
            result = storage_service.formatted_text_exists("test-id")
            assert result is False

    def test_should_handle_generic_notebooklm_save_exception(self, storage_service):
        """Should handle generic exception when saving NotebookLM guideline."""
        with patch.object(Path, 'write_bytes', side_effect=RuntimeError("Write failed")):
            with pytest.raises(RuntimeError, match="Write failed"):
                storage_service.save_notebooklm_guideline("error-notebooklm", "Guideline text")

    def test_should_handle_generic_notebooklm_read_exception(self, storage_service):
        """Should handle generic exception when reading NotebookLM guideline."""
        transcription_id = "notebooklm-read-error"

        # Create NotebookLM guideline file first
        storage_service.save_notebooklm_guideline(transcription_id, "Guideline text")

        # Mock read_bytes to raise exception
        with patch.object(Path, 'read_bytes', side_effect=RuntimeError("Read failed")):
            with pytest.raises(RuntimeError, match="Read failed"):
                storage_service.get_notebooklm_guideline(transcription_id)

    def test_should_handle_generic_notebooklm_delete_exception(self, storage_service):
        """Should handle generic exception when deleting NotebookLM guideline."""
        transcription_id = "notebooklm-delete-error"

        # Create NotebookLM guideline file first
        storage_service.save_notebooklm_guideline(transcription_id, "Guideline text")

        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=RuntimeError("Delete failed")):
            result = storage_service.delete_notebooklm_guideline(transcription_id)
            assert result is False

    def test_should_handle_notebooklm_exists_exception(self, storage_service):
        """Should handle exception in notebooklm_guideline_exists."""
        with patch.object(Path, 'exists', side_effect=RuntimeError("Check failed")):
            result = storage_service.notebooklm_guideline_exists("test-id")
            assert result is False

    def test_should_handle_corrupted_gzip_data(self, storage_service):
        """Should handle corrupted gzip data."""
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        transcription_id = "corrupted-data"

        # Write corrupted gzip data
        file_path = TRANSCRIPTIONS_DIR / f"{transcription_id}.txt.gz"
        file_path.write_bytes(b"not valid gzip data")

        with pytest.raises(Exception):
            storage_service.get_transcription_text(transcription_id)

    def test_should_handle_corrupted_json_data(self, storage_service):
        """Should handle corrupted JSON data in segments."""
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        transcription_id = "corrupted-json"

        # Write invalid JSON data (but valid gzip)
        import gzip
        file_path = TRANSCRIPTIONS_DIR / f"{transcription_id}.segments.json.gz"
        corrupted_data = gzip.compress(b"not valid json data")
        file_path.write_bytes(corrupted_data)

        with pytest.raises(json.JSONDecodeError):
            storage_service.get_transcription_segments(transcription_id)

    def test_should_handle_permission_denied_on_write(self, storage_service):
        """Should handle permission denied when writing."""
        with patch.object(Path, 'write_bytes', side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError, match="Access denied"):
                storage_service.save_transcription_text("permission-error", "Test content")

