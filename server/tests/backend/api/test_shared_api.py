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


@pytest.mark.integration
class TestSharedChat:
    """Test shared transcription chat endpoint."""

    def test_shared_chat_nonexistent_token_returns_404(self, test_client: TestClient) -> None:
        """Test chat with non-existent share token returns 404."""
        fake_token = "nonexistent_token"
        response = test_client.post(
            f"/api/shared/{fake_token}/chat",
            json={"content": "Hello"}
        )
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    def test_shared_chat_expired_link_returns_410(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with expired share link returns 410."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-expired-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_expired.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create expired share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="expired_chat_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.post(
                "/api/shared/expired_chat_token/chat",
                json={"content": "Hello"}
            )
            assert response.status_code == 410
            assert "过期" in response.json()["detail"] or "expired" in response.json()["detail"].lower()
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "expired_chat_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_empty_message_returns_400(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with empty message returns 400."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-empty-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_empty.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create valid share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="empty_msg_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Test with empty content
            response = test_client.post(
                "/api/shared/empty_msg_token/chat",
                json={"content": ""}
            )
            assert response.status_code == 400
            assert "不能为空" in response.json()["detail"] or "empty" in response.json()["detail"].lower()

            # Test with whitespace only
            response = test_client.post(
                "/api/shared/empty_msg_token/chat",
                json={"content": "   "}
            )
            assert response.status_code == 400
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "empty_msg_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_rate_limiting(self, test_client: TestClient, db_session: Session) -> None:
        """Test rate limiting for shared chat endpoint."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-rate-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_rate.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="rate_limit_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Send requests up to the rate limit (10 requests)
            for i in range(10):
                response = test_client.post(
                    "/api/shared/rate_limit_token/chat",
                    json={"content": f"Message {i}"}
                )
                # First 10 should be allowed (may return 200 or 500 if GLM fails, but not 429)
                assert response.status_code != 429, f"Request {i+1} should not be rate limited yet"

            # 11th request should be rate limited
            response = test_client.post(
                "/api/shared/rate_limit_token/chat",
                json={"content": "Message 11"}
            )
            assert response.status_code == 429
            assert "频繁" in response.json()["detail"] or "rate" in response.json()["detail"].lower()
        finally:
            # Clean up rate limit store
            from app.core.rate_limit import clear_rate_limit
            clear_rate_limit("127.0.0.1")

            db_session.query(ShareLink).filter(ShareLink.share_token == "rate_limit_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_valid_request_structure(self, test_client: TestClient, db_session: Session) -> None:
        """Test that valid chat request returns expected response structure."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-valid-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_valid.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="valid_chat_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.post(
                "/api/shared/valid_chat_token/chat",
                json={"content": "What is this about?"}
            )
            # May return 200 (success) or 500 (GLM error), but not 4xx
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "role" in data
                assert data["role"] == "assistant"
                assert "content" in data
                assert isinstance(data["content"], str)
                assert "created_at" in data
            else:
                # GLM error case
                assert "失败" in response.json()["detail"] or "error" in response.json()["detail"].lower()
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "valid_chat_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()
