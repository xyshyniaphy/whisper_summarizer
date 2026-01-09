"""
Shared API Tests

Tests for shared transcription endpoints (share links).
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.summary import Summary
from app.models.share_link import ShareLink


@pytest.mark.integration
class TestGetSharedTranscription:
    """Test get shared transcription endpoint."""

    def test_get_shared_nonexistent_link_returns_404(self, test_client: TestClient) -> None:
        """Get shared transcription with non-existent token returns 404."""
        fake_token = "nonexistent_token"
        response = test_client.get(f"/api/shared/{fake_token}")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    def test_get_shared_expired_link_returns_410(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription with expired link returns 410."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)

        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_shared.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create expired share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="expired_token_123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.get("/api/shared/expired_token_123")
            assert response.status_code == 410
            assert "过期" in response.json()["detail"] or "expired" in response.json()["detail"].lower()
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "expired_token_123").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_get_shared_valid_link_returns_transcription(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription with valid link returns transcription data."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-valid-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)

        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_shared_valid.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create valid share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="valid_token_123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.get("/api/shared/valid_token_123")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(tid)
            assert data["file_name"] == "test_shared_valid.mp3"
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "valid_token_123").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()
