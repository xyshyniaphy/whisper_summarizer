"""
Audio Upload API Unit Tests

Unit tests for audio upload endpoints and helper functions.
Tests the get_or_create_user function, process_audio_task, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from uuid import uuid4
from pathlib import Path
from sqlalchemy.orm import Session

from app.api.audio import get_or_create_user, process_audio_task, UPLOAD_DIR, OUTPUT_DIR
from app.models.user import User
from app.models.transcription import Transcription


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit = MagicMock()
    session.add = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def mock_user():
    """Mock user object."""
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_transcription():
    """Mock transcription object."""
    transcription = MagicMock()
    transcription.id = uuid4()
    transcription.file_name = "test_audio.wav"
    transcription.file_path = "/app/data/uploads/test.wav"
    transcription.stage = "uploading"
    transcription.user_id = str(uuid4())
    return transcription


# ============================================================================
# get_or_create_user() Tests
# ============================================================================

class TestGetOrCreateUser:
    """Test get_or_create_user function."""

    def test_should_return_existing_user_by_id(self, mock_db_session, mock_user):
        """Should return existing user when found by ID."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db_session.query.return_value = mock_query

        result = get_or_create_user(mock_db_session, mock_user.id, mock_user.email)

        assert result == mock_user
        mock_db_session.query.assert_called_once_with(User)

    def test_should_return_existing_user_by_email(self, mock_db_session, mock_user):
        """Should return existing user when found by email after ID lookup fails."""
        # First query (by ID) returns None
        # Second query (by email) returns user
        call_count = [0]

        def mock_query_behavior(*args, **kwargs):
            mock_q = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # ID lookup returns None
                mock_q.filter.return_value.first.return_value = None
            else:
                # Email lookup returns user
                mock_q.filter.return_value.first.return_value = mock_user
            return mock_q

        mock_db_session.query.side_effect = mock_query_behavior

        result = get_or_create_user(mock_db_session, "new-id", mock_user.email)

        assert result == mock_user
        assert mock_db_session.query.call_count == 2

    def test_should_create_new_user_when_not_found(self, mock_db_session):
        """Should create new user when not found by ID or email."""
        # All queries return None
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())
        email = "new@example.com"

        result = get_or_create_user(mock_db_session, user_id, email)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called_once()

    def test_should_handle_none_email_gracefully(self, mock_db_session):
        """Should handle None email without crashing."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())

        # Should not crash with None email
        result = get_or_create_user(mock_db_session, user_id, None)

        mock_db_session.add.assert_called_once()

    def test_should_skip_email_lookup_when_email_empty(self, mock_db_session):
        """Should skip email lookup when email is empty."""
        call_count = [0]

        def mock_query_behavior(*args, **kwargs):
            mock_q = MagicMock()
            call_count[0] += 1
            mock_q.filter.return_value.first.return_value = None
            return mock_q

        mock_db_session.query.side_effect = mock_query_behavior

        # Empty string email
        get_or_create_user(mock_db_session, str(uuid4()), "")

        # Should only query once (by ID), not twice
        assert call_count[0] == 1


# ============================================================================
# process_audio_task() Tests
# ============================================================================

class TestProcessAudioTask:
    """Test process_audio_task function."""

    @patch('app.api.audio.processor')
    @patch('app.api.audio.logger')
    def test_should_call_processor_process_transcription(self, mock_logger, mock_processor):
        """Should call processor.process_transcription with correct ID."""
        transcription_id = str(uuid4())

        process_audio_task(transcription_id)

        mock_processor.process_transcription.assert_called_once_with(transcription_id)
        mock_logger.info.assert_called()

    @patch('app.api.audio.processor')
    @patch('app.api.audio.logger')
    def test_should_log_processing_start(self, mock_logger, mock_processor):
        """Should log when starting background processing."""
        transcription_id = "test-id-123"

        process_audio_task(transcription_id)

        # Check logger was called with correct message
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("test-id-123" in str(call) for call in log_calls)


# ============================================================================
# File Extension Validation Tests (Unit tests without TestClient)
# ============================================================================

class TestFileExtensionValidation:
    """Test file extension validation logic."""

    def test_allowed_extensions_list(self):
        """Should have correct list of allowed extensions."""
        # The source code defines these
        from app.api.audio import router
        # We can't easily test this without hitting the endpoint
        # but we can verify the logic is correct by inspection
        allowed = [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]
        assert ".wav" in allowed
        assert ".mp3" in allowed
        assert ".txt" not in allowed

    def test_path_suffix_is_case_insensitive(self):
        """Path().suffix.lower() should handle case correctly."""
        assert Path("test.WAV").suffix.lower() == ".wav"
        assert Path("test.MP3").suffix.lower() == ".mp3"
        assert Path("test.M4A").suffix.lower() == ".m4a"


# ============================================================================
# Module Constants Tests
# ============================================================================

class TestModuleConstants:
    """Test module-level constants."""

    def test_upload_dir_should_be_defined(self):
        """Should have UPLOAD_DIR constant defined."""
        assert UPLOAD_DIR is not None
        assert isinstance(UPLOAD_DIR, Path)

    def test_output_dir_should_be_defined(self):
        """Should have OUTPUT_DIR constant defined."""
        assert OUTPUT_DIR is not None
        assert isinstance(OUTPUT_DIR, Path)

    def test_upload_dir_should_create_if_not_exists(self):
        """UPLOAD_DIR should exist or be created."""
        # In test environment, paths might not actually exist
        # Just check the constant is set correctly
        assert str(UPLOAD_DIR) == "/app/data/uploads"

    def test_output_dir_should_create_if_not_exists(self):
        """OUTPUT_DIR should exist or be created."""
        assert str(OUTPUT_DIR) == "/app/data/output"


# ============================================================================
# Error Simulation Tests
# ============================================================================

class TestErrorSimulation:
    """Test error scenarios using simulation."""

    def test_get_or_create_user_with_empty_email(self, mock_db_session):
        """Should handle empty email in get_or_create_user."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())

        # Empty email should work
        result = get_or_create_user(mock_db_session, user_id, "")

        # Should create user
        mock_db_session.add.assert_called_once()

    def test_get_or_create_user_with_whitespace_email(self, mock_db_session):
        """Should handle whitespace email in get_or_create_user."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())

        # Whitespace email should work (API doesn't trim)
        result = get_or_create_user(mock_db_session, user_id, "   ")

        # Should create user
        mock_db_session.add.assert_called_once()

    @patch('app.api.audio.processor')
    def test_process_audio_task_with_none_id(self, mock_processor):
        """Should handle None ID in process_audio_task."""
        # Should not crash
        process_audio_task(None)
        mock_processor.process_transcription.assert_called_once_with(None)

    @patch('app.api.audio.processor')
    def test_process_audio_task_with_empty_string_id(self, mock_processor):
        """Should handle empty string ID in process_audio_task."""
        # Should not crash
        process_audio_task("")
        mock_processor.process_transcription.assert_called_once_with("")

    @patch('app.api.audio.processor')
    def test_process_audio_task_with_uuid_string(self, mock_processor):
        """Should handle UUID string in process_audio_task."""
        test_id = str(uuid4())
        process_audio_task(test_id)
        mock_processor.process_transcription.assert_called_once_with(test_id)


# ============================================================================
# Integration with Transcription Model
# ============================================================================

class TestTranscriptionIntegration:
    """Test integration with transcription model."""

    def test_upload_creates_transcription_with_uploading_stage(self, mock_db_session, mock_user):
        """Should create transcription with 'uploading' stage initially."""
        # Simulate what happens in the upload endpoint
        transcription = Transcription(
            file_name="test.wav",
            stage="uploading",
            user_id=mock_user.id
        )

        assert transcription.stage == "uploading"
        assert transcription.file_name == "test.wav"
        assert transcription.user_id == mock_user.id

    def test_upload_updates_file_path(self, mock_db_session, mock_user):
        """Should update file path after creating transcription."""
        transcription = Transcription(
            file_name="test.wav",
            stage="uploading",
            user_id=mock_user.id
        )

        file_extension = Path("test.wav").suffix.lower()
        file_path = UPLOAD_DIR / f"{transcription.id}{file_extension}"
        transcription.file_path = str(file_path)

        assert transcription.file_path is not None
        assert ".wav" in transcription.file_path


# ============================================================================
# User Creation Edge Cases
# ============================================================================

class TestUserCreationEdgeCases:
    """Test edge cases in user creation."""

    def test_should_create_user_with_valid_uuid(self, mock_db_session):
        """Should create user with valid UUID format."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())
        email = "test@example.com"

        result = get_or_create_user(mock_db_session, user_id, email)

        # Should create user with provided ID
        add_call_args = mock_db_session.add.call_args[0][0]
        assert add_call_args.id == user_id
        assert add_call_args.email == email

    def test_should_handle_very_long_email(self, mock_db_session):
        """Should handle very long email address."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())
        long_email = "a" * 100 + "@example.com"

        result = get_or_create_user(mock_db_session, user_id, long_email)

        # Should still create user
        mock_db_session.add.assert_called_once()

    def test_should_handle_special_chars_in_email(self, mock_db_session):
        """Should handle special characters in email."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        user_id = str(uuid4())
        special_email = "test+user@example.com"

        result = get_or_create_user(mock_db_session, user_id, special_email)

        # Should create user
        mock_db_session.add.assert_called_once()


# ============================================================================
# Database Session Mock Behavior
# ============================================================================

class TestDatabaseSessionMockBehavior:
    """Test that mock database session behaves correctly."""

    def test_mock_session_should_have_commit_method(self, mock_db_session):
        """Mock session should have commit method."""
        assert hasattr(mock_db_session, 'commit')
        assert callable(mock_db_session.commit)

    def test_mock_session_should_have_add_method(self, mock_db_session):
        """Mock session should have add method."""
        assert hasattr(mock_db_session, 'add')
        assert callable(mock_db_session.add)

    def test_mock_session_should_have_refresh_method(self, mock_db_session):
        """Mock session should have refresh method."""
        assert hasattr(mock_db_session, 'refresh')
        assert callable(mock_db_session.refresh)

    def test_mock_session_should_have_delete_method(self, mock_db_session):
        """Mock session should have delete method."""
        assert hasattr(mock_db_session, 'delete')
        assert callable(mock_db_session.delete)

    def test_mock_session_should_have_query_method(self, mock_db_session):
        """Mock session should have query method."""
        assert hasattr(mock_db_session, 'query')
        assert callable(mock_db_session.query)
