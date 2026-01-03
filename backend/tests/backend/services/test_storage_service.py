"""
Tests for StorageService - Local file storage operations.
"""

import pytest
import gzip
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.storage_service import (
    StorageService,
    get_storage_service,
    TRANSCRIPTIONS_DIR
)


@pytest.fixture
def mock_storage_dir(tmp_path):
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "transcribes"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def storage_service(mock_storage_dir):
    """Create a StorageService instance with mocked directory."""
    with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', mock_storage_dir):
        service = StorageService()
        yield service


class TestStorageServiceInitialization:
    """Tests for StorageService initialization."""

    def test_creates_directory_on_init(self, tmp_path):
        """Test that StorageService creates directory on initialization."""
        storage_dir = tmp_path / "new_storage"
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', storage_dir):
            service = StorageService()
            assert storage_dir.exists()
            assert storage_dir.is_dir()

    def test_existing_directory_is_ok(self, mock_storage_dir):
        """Test that existing directory doesn't cause issues."""
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', mock_storage_dir):
            service = StorageService()
            assert service is not None


class TestTranscriptionTextStorage:
    """Tests for transcription text save/load/delete operations."""

    def test_save_transcription_text(self, storage_service, mock_storage_dir):
        """Test saving transcription text as gzip file."""
        transcription_id = "test-id-123"
        text = "This is a test transcription text."

        storage_path = storage_service.save_transcription_text(transcription_id, text)

        # Check file exists
        expected_path = mock_storage_dir / f"{transcription_id}.txt.gz"
        assert expected_path.exists()
        assert storage_path == f"{transcription_id}.txt.gz"

    def test_save_with_custom_compression_level(self, storage_service, mock_storage_dir):
        """Test saving with custom compression level."""
        transcription_id = "test-id-compression"
        text = "x" * 1000  # Repeat character to test compression

        # Save with different compression levels
        path1 = storage_service.save_transcription_text(transcription_id + "1", text, compression_level=1)
        path2 = storage_service.save_transcription_text(transcription_id + "2", text, compression_level=9)

        file1 = mock_storage_dir / f"{transcription_id}1.txt.gz"
        file2 = mock_storage_dir / f"{transcription_id}2.txt.gz"

        # Higher compression should result in smaller file
        assert file2.stat().st_size < file1.stat().st_size

    def test_get_transcription_text(self, storage_service, mock_storage_dir):
        """Test reading and decompressing transcription text."""
        transcription_id = "test-id-read"
        original_text = "This is the original transcription text."

        # Save first
        storage_service.save_transcription_text(transcription_id, original_text)

        # Then read
        retrieved_text = storage_service.get_transcription_text(transcription_id)

        assert retrieved_text == original_text

    def test_get_transcription_text_not_found(self, storage_service):
        """Test reading non-existent transcription raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_transcription_text("non-existent-id")

    def test_get_transcription_text_unicode(self, storage_service):
        """Test reading transcription with Unicode content."""
        transcription_id = "test-id-unicode"
        text = "中文测试 🎉 Test with emoji and unicode"

        storage_service.save_transcription_text(transcription_id, text)
        retrieved = storage_service.get_transcription_text(transcription_id)

        assert retrieved == text

    def test_delete_transcription_text(self, storage_service, mock_storage_dir):
        """Test deleting transcription text."""
        transcription_id = "test-id-delete"
        text = "Text to delete"

        # Save first
        storage_service.save_transcription_text(transcription_id, text)
        file_path = mock_storage_dir / f"{transcription_id}.txt.gz"
        assert file_path.exists()

        # Delete
        result = storage_service.delete_transcription_text(transcription_id)
        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent_transcription(self, storage_service):
        """Test deleting non-existent transcription returns False."""
        result = storage_service.delete_transcription_text("non-existent")
        assert result is False

    def test_transcription_exists(self, storage_service):
        """Test checking if transcription exists."""
        transcription_id = "test-id-exists"
        text = "Exists check"

        # Not exists initially
        assert storage_service.transcription_exists(transcription_id) is False

        # Save
        storage_service.save_transcription_text(transcription_id, text)

        # Now exists
        assert storage_service.transcription_exists(transcription_id) is True


class TestTranscriptionSegmentsStorage:
    """Tests for transcription segments save/load/delete operations."""

    def test_save_transcription_segments(self, storage_service, mock_storage_dir):
        """Test saving transcription segments."""
        transcription_id = "test-segments-id"
        segments = [
            {"start": 0.0, "end": 2.5, "text": "First segment"},
            {"start": 2.5, "end": 5.0, "text": "Second segment"},
        ]

        storage_path = storage_service.save_transcription_segments(transcription_id, segments)

        expected_path = mock_storage_dir / f"{transcription_id}.segments.json.gz"
        assert expected_path.exists()
        assert storage_path == f"{transcription_id}.segments.json.gz"

    def test_get_transcription_segments(self, storage_service):
        """Test reading transcription segments."""
        transcription_id = "test-get-segments"
        original_segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": "World"},
        ]

        storage_service.save_transcription_segments(transcription_id, original_segments)
        retrieved_segments = storage_service.get_transcription_segments(transcription_id)

        assert retrieved_segments == original_segments

    def test_get_segments_returns_empty_list_if_not_found(self, storage_service):
        """Test that get_segments returns empty list when file doesn't exist."""
        segments = storage_service.get_transcription_segments("non-existent")
        assert segments == []

    def test_delete_transcription_segments(self, storage_service, mock_storage_dir):
        """Test deleting transcription segments."""
        transcription_id = "test-delete-segments"
        segments = [{"start": 0.0, "end": 1.0, "text": "Delete me"}]

        storage_service.save_transcription_segments(transcription_id, segments)
        file_path = mock_storage_dir / f"{transcription_id}.segments.json.gz"
        assert file_path.exists()

        result = storage_service.delete_transcription_segments(transcription_id)
        assert result is True
        assert not file_path.exists()

    def test_segments_exist(self, storage_service):
        """Test checking if segments exist."""
        transcription_id = "test-segments-exist"
        segments = [{"start": 0.0, "end": 1.0, "text": "Check"}]

        assert storage_service.segments_exist(transcription_id) is False

        storage_service.save_transcription_segments(transcription_id, segments)
        assert storage_service.segments_exist(transcription_id) is True


class TestOriginalOutputStorage:
    """Tests for original whisper output storage."""

    def test_save_and_get_original_output(self, storage_service):
        """Test saving and reading original output."""
        transcription_id = "test-original"
        original = {
            "segments": [{"start": 0, "end": 1, "text": "Test"}],
            "language": "zh",
            "duration": 10.5
        }

        storage_service.save_original_output(transcription_id, original)
        retrieved = storage_service.get_original_output(transcription_id)

        assert retrieved == original
        assert retrieved["language"] == "zh"

    def test_get_original_returns_none_if_not_found(self, storage_service):
        """Test that get_original_output returns None when not found."""
        result = storage_service.get_original_output("non-existent")
        assert result is None

    def test_delete_original_output(self, storage_service, mock_storage_dir):
        """Test deleting original output."""
        transcription_id = "test-delete-original"
        original = {"test": "data"}

        storage_service.save_original_output(transcription_id, original)
        file_path = mock_storage_dir / f"{transcription_id}.original.json.gz"
        assert file_path.exists()

        result = storage_service.delete_original_output(transcription_id)
        assert result is True
        assert not file_path.exists()


class TestFormattedTextStorage:
    """Tests for formatted text storage."""

    def test_save_and_get_formatted_text(self, storage_service):
        """Test saving and reading formatted text."""
        transcription_id = "test-formatted"
        formatted = "# Formatted Transcription\n\nThis is a formatted version."

        storage_service.save_formatted_text(transcription_id, formatted)
        retrieved = storage_service.get_formatted_text(transcription_id)

        assert retrieved == formatted

    def test_delete_formatted_text(self, storage_service, mock_storage_dir):
        """Test deleting formatted text."""
        transcription_id = "test-delete-formatted"
        formatted = "Formatted text to delete"

        storage_service.save_formatted_text(transcription_id, formatted)
        file_path = mock_storage_dir / f"{transcription_id}.formatted.txt.gz"
        assert file_path.exists()

        result = storage_service.delete_formatted_text(transcription_id)
        assert result is True
        assert not file_path.exists()

    def test_formatted_text_exists(self, storage_service):
        """Test checking if formatted text exists."""
        transcription_id = "test-formatted-exists"

        assert storage_service.formatted_text_exists(transcription_id) is False

        storage_service.save_formatted_text(transcription_id, "Test")
        assert storage_service.formatted_text_exists(transcription_id) is True


class TestNotebookLMGuidelineStorage:
    """Tests for NotebookLM guideline storage."""

    def test_save_and_get_notebooklm_guideline(self, storage_service):
        """Test saving and reading NotebookLM guideline."""
        transcription_id = "test-notebooklm"
        guideline = "NotebookLM guideline content here."

        storage_service.save_notebooklm_guideline(transcription_id, guideline)
        retrieved = storage_service.get_notebooklm_guideline(transcription_id)

        assert retrieved == guideline

    def test_delete_notebooklm_guideline(self, storage_service, mock_storage_dir):
        """Test deleting NotebookLM guideline."""
        transcription_id = "test-delete-notebooklm"
        guideline = "Guideline to delete"

        storage_service.save_notebooklm_guideline(transcription_id, guideline)
        file_path = mock_storage_dir / f"{transcription_id}.notebooklm.txt.gz"
        assert file_path.exists()

        result = storage_service.delete_notebooklm_guideline(transcription_id)
        assert result is True
        assert not file_path.exists()

    def test_notebooklm_guideline_exists(self, storage_service):
        """Test checking if guideline exists."""
        transcription_id = "test-guideline-exists"

        assert storage_service.notebooklm_guideline_exists(transcription_id) is False

        storage_service.save_notebooklm_guideline(transcription_id, "Test")
        assert storage_service.notebooklm_guideline_exists(transcription_id) is True


class TestSingletonFunction:
    """Tests for get_storage_service singleton function."""

    def test_get_storage_service_returns_singleton(self):
        """Test that get_storage_service returns same instance."""
        with patch('app.services.storage_service.TRANSCRIPTIONS_DIR', Path("/tmp/test")):
            service1 = get_storage_service()
            service2 = get_storage_service()

            # Should be the same instance (before reset)
            assert service1 is service2

    def test_get_storage_service_initializes_once(self):
        """Test that storage service is initialized only once."""
        with patch('app.services.storage_service.StorageService') as MockStorage:
            mock_instance = Mock()
            MockStorage.return_value = mock_instance

            with patch('app.services.storage_service._storage_service', None):
                get_storage_service()
                get_storage_service()

                # Should only initialize once
                MockStorage.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in storage operations."""

    def test_save_error_propagates(self, storage_service):
        """Test that save errors are propagated."""
        with patch('pathlib.Path.write_bytes', side_effect=IOError("Disk full")):
            with pytest.raises(Exception):
                storage_service.save_transcription_text("test-id", "text")

    def test_get_error_propagates_for_corrupt_file(self, storage_service, mock_storage_dir):
        """Test that reading corrupt gzip file raises error."""
        # Create a corrupt gzip file
        transcription_id = "corrupt"
        corrupt_file = mock_storage_dir / f"{transcription_id}.txt.gz"
        corrupt_file.write_bytes(b"not a valid gzip file")

        with pytest.raises(Exception):
            storage_service.get_transcription_text(transcription_id)
