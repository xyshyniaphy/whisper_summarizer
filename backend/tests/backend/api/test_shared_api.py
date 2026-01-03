"""
Tests for Shared Transcription API endpoints.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.shared import router
from app.models.transcription import Transcription
from app.models.share_link import ShareLink
from app.schemas.share import SharedTranscriptionResponse


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/shared")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


class TestGetSharedTranscription:
    """Tests for GET /api/shared/{share_token} endpoint."""

    def test_valid_share_link(self, client, mock_db):
        """Test accessing transcription via valid share link."""
        # Create mock transcription
        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.file_name = "test_audio.mp3"
        mock_transcription.text = "Transcription text here"
        mock_transcription.language = "zh"
        mock_transcription.duration_seconds = 120
        mock_transcription.created_at = datetime.now(timezone.utc)
        mock_transcription.summaries = []

        # Create mock share link
        mock_share_link = Mock()
        mock_share_link.share_token = "valid-token-123"
        mock_share_link.transcription_id = "transcription-123"
        mock_share_link.expires_at = None
        mock_share_link.access_count = 5

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/valid-token-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "transcription-123"
        assert data["file_name"] == "test_audio.mp3"
        assert data["text"] == "Transcription text here"

    def test_nonexistent_share_token(self, client, mock_db):
        """Test that non-existent share token returns 404."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/api/shared/nonexistent-token")

        assert response.status_code == 404
        assert "分享链接不存在" in response.json()["detail"]

    def test_expired_share_link(self, client, mock_db):
        """Test that expired share link returns 410."""
        mock_share_link = Mock()
        mock_share_link.share_token = "expired-token"
        mock_share_link.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_share_link

        response = client.get("/api/shared/expired-token")

        assert response.status_code == 410
        assert "分享链接已过期" in response.json()["detail"]

    def test_nonexistent_transcription(self, client, mock_db):
        """Test that missing transcription returns 404."""
        mock_share_link = Mock()
        mock_share_link.share_token = "valid-token"
        mock_share_link.transcription_id = "missing-transcription"
        mock_share_link.expires_at = None

        # Share link exists but transcription doesn't
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, None]

        response = client.get("/api/shared/valid-token")

        assert response.status_code == 404
        assert "转录不存在" in response.json()["detail"]

    def test_access_count_incremented(self, client, mock_db):
        """Test that access count is incremented."""
        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.summaries = []

        mock_share_link = Mock()
        mock_share_link.share_token = "token-123"
        mock_share_link.transcription_id = "transcription-123"
        mock_share_link.expires_at = None
        mock_share_link.access_count = 10

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/token-123")

        assert response.status_code == 200
        assert mock_share_link.access_count == 11
        mock_db.commit.assert_called_once()

    def test_includes_summary_when_available(self, client, mock_db):
        """Test that summary is included when available."""
        mock_summary = Mock()
        mock_summary.summary_text = "AI generated summary"

        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.file_name = "test.mp3"
        mock_transcription.text = "Text"
        mock_transcription.language = "zh"
        mock_transcription.duration_seconds = 60
        mock_transcription.created_at = datetime.now(timezone.utc)
        mock_transcription.summaries = [mock_summary]

        mock_share_link = Mock()
        mock_share_link.share_token = "token-123"
        mock_share_link.transcription_id = "transcription-123"
        mock_share_link.expires_at = None
        mock_share_link.access_count = 0

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/token-123")

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "AI generated summary"

    def test_no_summary_when_unavailable(self, client, mock_db):
        """Test that summary is None when not available."""
        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.summaries = []

        mock_share_link = Mock()
        mock_share_link.share_token = "token-123"
        mock_share_link.transcription_id = "transcription-123"
        mock_share_link.expires_at = None

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/token-123")

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] is None

    def test_includes_all_response_fields(self, client, mock_db):
        """Test that all expected fields are in response."""
        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.file_name = "test.mp3"
        mock_transcription.text = "Full text content"
        mock_transcription.language = "en"
        mock_transcription.duration_seconds = 300
        mock_transcription.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_transcription.summaries = []

        mock_share_link = Mock()
        mock_share_link.share_token = "token-123"
        mock_share_link.transcription_id = "transcription-123"
        mock_share_link.expires_at = None

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/token-123")

        assert response.status_code == 200
        data = response.json()

        # Check all fields
        assert "id" in data
        assert "file_name" in data
        assert "text" in data
        assert "summary" in data
        assert "language" in data
        assert "duration_seconds" in data
        assert "created_at" in data

    def test_handles_future_expiration(self, client, mock_db):
        """Test that share links with future expiration are accepted."""
        future_time = datetime.now(timezone.utc) + timedelta(days=30)

        mock_share_link = Mock()
        mock_share_link.share_token = "token-123"
        mock_share_link.expires_at = future_time
        mock_share_link.transcription_id = "transcription-123"

        mock_transcription = Mock()
        mock_transcription.id = "transcription-123"
        mock_transcription.summaries = []

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_share_link, mock_transcription]

        response = client.get("/api/shared/token-123")

        assert response.status_code == 200


class TestSharedTranscriptionResponseModel:
    """Tests for SharedTranscriptionResponse schema."""

    def test_response_schema_structure(self):
        """Test that response schema has correct structure."""
        response = SharedTranscriptionResponse(
            id="test-id",
            file_name="test.mp3",
            text="Transcription text",
            summary="Summary text",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc)
        )

        assert response.id == "test-id"
        assert response.file_name == "test.mp3"
        assert response.text == "Transcription text"
        assert response.summary == "Summary text"
        assert response.language == "zh"
        assert response.duration_seconds == 120
