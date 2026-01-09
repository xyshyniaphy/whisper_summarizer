"""
Transcriptions API Missing Coverage Tests

Tests for uncovered code paths in transcriptions.py to improve coverage from 85%.
Focus areas:
- Formatted text download with storage files
- SRT download with segments
- SRT download backward compatibility (no segments)
"""

import pytest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.summary import Summary
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel


@pytest.fixture
def test_user_with_channel(db_session: Session) -> dict:
    """Create test user with channel membership."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"test-download-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=None
    )
    db_session.add(user)
    db_session.flush()

    # Create channel
    cid = uuid.uuid4()
    channel = Channel(
        id=cid,
        name="Test Channel Downloads",
        description="Test channel for download tests"
    )
    db_session.add(channel)
    db_session.flush()

    # Add user to channel
    membership = ChannelMembership(
        channel_id=cid,
        user_id=uid
    )
    db_session.add(membership)
    db_session.commit()

    return {
        "id": str(uid),
        "email": user.email,
        "channel_id": str(cid),
        "raw_uuid": uid
    }


@pytest.fixture
def activated_test_user_with_channel(test_user_with_channel: dict, db_session: Session) -> dict:
    """Activate the test user."""
    from datetime import datetime, timezone

    user = db_session.query(User).filter(User.id == test_user_with_channel["raw_uuid"]).first()
    if user:
        user.is_active = True
        user.activated_at = datetime.now(timezone.utc)
        db_session.commit()

    return test_user_with_channel


@pytest.fixture
def download_auth_client(test_user_with_channel: dict, db_session: Session) -> TestClient:
    """Authenticated test client for download tests."""
    from app.main import app
    from app.core.supabase import get_current_active_user

    async def override_auth():
        return {
            "id": test_user_with_channel["id"],
            "email": test_user_with_channel["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": False, "is_active": True}
        }

    app.dependency_overrides[get_current_active_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestDownloadFormattedText:
    """Test formatted text download endpoint."""

    def test_download_formatted_text_with_file(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """Download formatted text when storage file exists."""
        from app.services.storage_service import get_storage_service

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=test_user_with_channel["raw_uuid"],
            file_name="test_formatted.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Save original text and formatted text file in storage
        storage_service = get_storage_service()
        original_text = "Original transcription text here"
        formatted_text = "Formatted transcription with proper paragraphs and punctuation."
        storage_service.save_transcription_text(str(tid), original_text)
        storage_service.save_formatted_text(str(tid), formatted_text)

        try:
            response = download_auth_client.get(f"/api/transcriptions/{tid}/download?format=formatted")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert "formatted" in response.headers["content-disposition"]
            assert formatted_text == response.text
        finally:
            storage_service.delete_formatted_text(str(tid))
            storage_service.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()

    def test_download_formatted_text_fallback_to_original(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """Download formatted text falls back to original when file doesn't exist."""
        from app.services.storage_service import get_storage_service

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=test_user_with_channel["raw_uuid"],
            file_name="test_fallback.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Save original text but NOT formatted text
        storage_service = get_storage_service()
        original_text = "Original transcription text"
        storage_service.save_transcription_text(str(tid), original_text)

        try:
            response = download_auth_client.get(f"/api/transcriptions/{tid}/download?format=formatted")
            assert response.status_code == 200
            assert original_text in response.text
        finally:
            storage_service.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()


@pytest.mark.integration
class TestDownloadSRTWithSegments:
    """Test SRT download with segment timestamps."""

    def test_download_srt_with_segments(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """Download SRT using stored segments with real timestamps."""
        from app.services.storage_service import get_storage_service

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=test_user_with_channel["raw_uuid"],
            file_name="test_srt_segments.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Save transcription text and segments
        storage_service = get_storage_service()
        original_text = "Segment one text Segment two text Segment three text"
        storage_service.save_transcription_text(str(tid), original_text)

        segments = [
            {"start": "00:00:00,000", "end": "00:00:02,500", "text": "Segment one text"},
            {"start": "00:00:02,500", "end": "00:00:05,000", "text": "Segment two text"},
            {"start": "00:00:05,000", "end": "00:00:07,500", "text": "Segment three text"}
        ]
        storage_service.save_transcription_segments(str(tid), segments)

        try:
            response = download_auth_client.get(f"/api/transcriptions/{tid}/download?format=srt")
            assert response.status_code == 200
            content = response.text
            # Verify SRT format with real timestamps
            assert "1\n00:00:00,000 --> 00:00:02,500\nSegment one text" in content
            assert "2\n00:00:02,500 --> 00:00:05,000\nSegment two text" in content
            assert "3\n00:00:05,000 --> 00:00:07,500\nSegment three text" in content
        finally:
            storage_service.delete_transcription_segments(str(tid))
            storage_service.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()

    def test_download_srt_with_empty_segments(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """Download SRT falls back to fake timestamps when segments file is empty."""
        from app.services.storage_service import get_storage_service

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=test_user_with_channel["raw_uuid"],
            file_name="test_srt_empty.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Save text and empty segments
        storage_service = get_storage_service()
        original_text = "Test transcription for empty segments"
        storage_service.save_transcription_text(str(tid), original_text)
        storage_service.save_transcription_segments(str(tid), [])

        try:
            response = download_auth_client.get(f"/api/transcriptions/{tid}/download?format=srt")
            assert response.status_code == 200
            content = response.text
            # Should use fake timestamps as fallback
            assert "00:00:00,000 -->" in content or "-->" in content
        finally:
            storage_service.delete_transcription_segments(str(tid))
            storage_service.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()

    def test_download_srt_without_segments(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """Download SRT without segments file uses fake timestamps (backward compatibility)."""
        from app.services.storage_service import get_storage_service

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=test_user_with_channel["raw_uuid"],
            file_name="test_srt_compat.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Save text WITHOUT segments file
        storage_service = get_storage_service()
        original_text = "Test transcription for backward compatibility"
        storage_service.save_transcription_text(str(tid), original_text)

        try:
            response = download_auth_client.get(f"/api/transcriptions/{tid}/download?format=srt")
            assert response.status_code == 200
            content = response.text
            # Should use fake timestamps for backward compatibility
            assert "-->" in content
            assert "Test transcription for backward compatibility" in content
        finally:
            storage_service.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()

@pytest.mark.integration
class TestChannelFiltering:
    """Test channel filtering in transcriptions list."""

    @pytest.mark.skip(reason="Channel filtering is already tested in test_transcriptions_api.py")
    def test_list_transcriptions_with_channel_filter(self, download_auth_client: TestClient, test_user_with_channel: dict, db_session: Session) -> None:
        """List transcriptions filtered by channel ID."""
        # This test is skipped because channel filtering is already tested elsewhere
        pass
