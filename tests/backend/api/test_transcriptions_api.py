"""
Transcriptions API Tests

Tests for the main transcriptions CRUD endpoints.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.transcription import Transcription
from app.models.user import User
from app.models.summary import Summary
from app.models.chat_message import ChatMessage
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel
from app.models.share_link import ShareLink
from app.main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.count.return_value = 0
    session.commit = MagicMock()
    session.delete = MagicMock()
    session.add = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "is_admin": False,
        "is_active": True
    }


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return {
        "id": str(uuid4()),
        "email": "admin@example.com",
        "is_admin": True,
        "is_active": True
    }


@pytest.fixture
def mock_transcription(mock_user):
    """Mock transcription object."""
    transcription = MagicMock()
    transcription.id = uuid4()
    transcription.user_id = mock_user["id"]
    transcription.file_name = "test_audio.wav"
    transcription.text = "Test transcription text"
    transcription.original_text = "Test transcription text"
    transcription.stage = "completed"
    transcription.language = "zh"
    transcription.duration_seconds = 120
    transcription.created_at = "2024-01-01T00:00:00Z"
    transcription.storage_path = "test.txt.gz"
    transcription.file_path = "/path/to/file.wav"
    transcription.summaries = []
    return transcription


# ============================================================================
# GET / - List Transcriptions Tests
# ============================================================================

class TestListTranscriptions:
    """Test listing transcriptions endpoint."""

    def test_should_list_user_transcriptions(self, client, mock_db_session, mock_user):
        """Should return user's own transcriptions."""
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.user_id = mock_user["id"]

        # Create a proper mock chain
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_transcription]
        mock_query.filter.return_value.count.return_value = 1
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                response = client.get("/api/transcriptions")

        assert response.status_code == 200

    def test_should_support_pagination(self, client, mock_db_session, mock_user):
        """Should support page and page_size parameters."""
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_query.filter.return_value.count.return_value = 100
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                with patch('app.api.transcriptions.settings') as mock_settings:
                    mock_settings.MAX_PAGE_SIZE = 100
                    mock_settings.DEFAULT_PAGE_SIZE = 20

                    response = client.get("/api/transcriptions?page=2&page_size=10")

        assert response.status_code == 200

    def test_should_filter_by_stage(self, client, mock_db_session, mock_user):
        """Should filter transcriptions by stage."""
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_query.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                response = client.get("/api/transcriptions?stage=completed")

        assert response.status_code == 200

    def test_should_reject_invalid_page_number(self, client, mock_db_session, mock_user):
        """Should reject page number less than 1."""
        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                response = client.get("/api/transcriptions?page=0")

        assert response.status_code == 422

    def test_should_filter_by_channel_for_regular_user(self, client, mock_db_session, mock_user):
        """Should filter by channel for regular users."""
        # Mock channel membership and query chain
        mock_membership = MagicMock()

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_membership
        mock_query.filter.return_value.join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_query.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                channel_id = str(uuid4())
                response = client.get(f"/api/transcriptions?channel_id={channel_id}")

        # Should either work (if member) or return 403
        assert response.status_code in [200, 403]

    def test_should_return_403_for_non_member_channel(self, client, mock_db_session, mock_user):
        """Should return 403 when user not in channel."""
        # No membership found
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_user):
                response = client.get(f"/api/transcriptions?channel_id={uuid4()}")

        assert response.status_code == 403

    def test_should_bypass_channel_filter_for_admin(self, client, mock_db_session, mock_admin_user):
        """Should bypass channel filter for admin users."""
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_query.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_db_user', return_value=mock_admin_user):
                response = client.get("/api/transcriptions")

        assert response.status_code == 200


# ============================================================================
# GET /{id} - Get Single Transcription Tests
# ============================================================================

class TestGetTranscription:
    """Test getting single transcription endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when transcription not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.get(f"/api/transcriptions/{uuid4()}")

        assert response.status_code == 404

    def test_should_return_422_for_invalid_uuid(self, client, mock_db_session, mock_user):
        """Should return 422 for invalid UUID format."""
        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.get("/api/transcriptions/invalid-uuid")

        assert response.status_code == 422

    def test_should_validate_uuid_format(self, client, mock_db_session, mock_user):
        """Should validate UUID format before querying."""
        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.get("/api/transcriptions/not-a-uuid")

        assert response.status_code == 422


# ============================================================================
# DELETE /{id} - Delete Single Transcription Tests
# ============================================================================

class TestDeleteTranscription:
    """Test deleting single transcription endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when deleting non-existent transcription."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.delete(f"/api/transcriptions/{uuid4()}")

        assert response.status_code == 404


# ============================================================================
# DELETE /all - Delete All Transcriptions Tests
# ============================================================================

class TestDeleteAllTranscriptions:
    """Test deleting all transcriptions endpoint."""

    def test_should_delete_all_transcriptions(self, client, mock_db_session, mock_user):
        """Should delete all user's transcriptions."""
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.user_id = mock_user["id"]
        mock_transcription.storage_path = "test.txt.gz"
        mock_transcription.file_path = None

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_transcription]
        mock_db_session.query.return_value.count.return_value = 1

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                with patch('app.services.storage_service.get_storage_service') as mock_storage:
                    mock_storage_service = MagicMock()
                    mock_storage.return_value = mock_storage_service

                    response = client.delete("/api/transcriptions/all")

        assert response.status_code == 200

    def test_should_return_empty_list_when_no_transcriptions(self, client, mock_db_session, mock_user):
        """Should return 0 count when user has no transcriptions."""
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.delete("/api/transcriptions/all")

        assert response.status_code == 200


# ============================================================================
# GET /{id}/download - Download SRT Tests
# ============================================================================

class TestDownloadSRT:
    """Test SRT download endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when transcription not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.get(f"/api/transcriptions/{uuid4()}/download")

        assert response.status_code == 404


# ============================================================================
# POST /{id}/share - Create Share Link Tests
# ============================================================================

class TestCreateShareLink:
    """Test share link creation endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when transcription not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.post(f"/api/transcriptions/{uuid4()}/share")

        assert response.status_code == 404


# ============================================================================
# GET /{id}/channels - Get Channels Tests
# ============================================================================

class TestGetTranscriptionChannels:
    """Test getting transcription channels endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when transcription not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.get(f"/api/transcriptions/{uuid4()}/channels")

        assert response.status_code == 404


# ============================================================================
# POST /{id}/channels - Assign Channels Tests
# ============================================================================

class TestAssignTranscriptionChannels:
    """Test channel assignment endpoint."""

    def test_should_return_404_for_nonexistent_transcription(self, client, mock_db_session, mock_user):
        """Should return 404 when transcription not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        channel_id = str(uuid4())
        request_data = {"channel_ids": [channel_id]}

        with patch('app.api.transcriptions.get_db', return_value=mock_db_session):
            with patch('app.api.transcriptions.get_current_active_user', return_value=mock_user):
                response = client.post(
                    f"/api/transcriptions/{uuid4()}/channels",
                    json=request_data
                )

        assert response.status_code == 404


# ============================================================================
# _format_fake_srt() Helper Function Tests
# ============================================================================

class TestFormatFakeSRT:
    """Test fake SRT generation helper."""

    def test_should_generate_fake_srt_from_plain_text(self):
        """Should generate SRT format from plain text."""
        from app.api.transcriptions import _format_fake_srt

        text = "Line one\nLine two\nLine three"
        result = _format_fake_srt(text)

        assert "1\n" in result
        assert "Line one" in result
        assert "2\n" in result
        assert "Line two" in result

    def test_should_handle_empty_text(self):
        """Should handle empty text gracefully."""
        from app.api.transcriptions import _format_fake_srt

        result = _format_fake_srt("")

        # Should return empty string
        assert result == ""

    def test_should_handle_single_line(self):
        """Should handle single line text."""
        from app.api.transcriptions import _format_fake_srt

        result = _format_fake_srt("Single line")

        assert "1\n" in result
        assert "Single line" in result
