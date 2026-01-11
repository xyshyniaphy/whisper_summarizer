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

    def test_get_shared_deleted_transcription_returns_404(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription where transcription was deleted returns 404."""
        # Create test user and transcription first
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-orphan-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_orphan.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="orphaned_token"
        )
        db_session.add(link)
        db_session.commit()

        # Delete the transcription (simulating orphaned share link)
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.commit()

        try:
            response = test_client.get("/api/shared/orphaned_token")
            # Note: When transcription is deleted, share link still exists
            # The API checks for share link first (returns 200 or 404 depending on implementation)
            # Since the share link exists but transcription doesn't, it should return 404
            assert response.status_code == 404
            # The API returns "分享链接不存在" when it can't find the transcription
            assert "不存在" in response.json()["detail"]
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "orphaned_token").delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_get_shared_no_expiration_succeeds(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription with no expiration (expires_at=None) succeeds."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-no-exp-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_no_exp.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link with no expiration (expires_at=None)
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="no_exp_token",
            expires_at=None
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.get("/api/shared/no_exp_token")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(tid)
            assert data["file_name"] == "test_no_exp.mp3"
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "no_exp_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_get_shared_increments_access_count(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription increments access_count on each access."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-count-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_count.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="count_token",
            access_count=0
        )
        db_session.add(link)
        db_session.commit()

        try:
            # First access
            response = test_client.get("/api/shared/count_token")
            assert response.status_code == 200
            db_session.refresh(link)
            assert link.access_count == 1

            # Second access
            response = test_client.get("/api/shared/count_token")
            assert response.status_code == 200
            db_session.refresh(link)
            assert link.access_count == 2
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "count_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_get_shared_with_summary_includes_summary(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription with summary includes summary in response."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-summary-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_with_summary.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.flush()

        # Save transcription text using storage service
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        storage.save_transcription_text(str(tid), "Sample transcription text.")

        # Create summary
        summary = Summary(
            id=uuid.uuid4(),
            transcription_id=tid,
            summary_text="This is a test summary."
        )
        db_session.add(summary)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="with_summary_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.get("/api/shared/with_summary_token")
            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "This is a test summary."
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "with_summary_token").delete()
            db_session.query(Summary).filter(Summary.transcription_id == tid).delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_get_shared_without_summary_summary_is_null(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription without summary has null summary field."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-shared-no-summary-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_no_summary.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link (no summary created)
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="no_summary_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.get("/api/shared/no_summary_token")
            assert response.status_code == 200
            data = response.json()
            assert data["summary"] is None
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "no_summary_token").delete()
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

    def test_shared_chat_empty_message_returns_422(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with empty message returns 422 (validation error)."""
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
            # Test with empty content - Pydantic validates min_length=1
            response = test_client.post(
                "/api/shared/empty_msg_token/chat",
                json={"content": ""}
            )
            # Pydantic validation returns 422, not 400
            assert response.status_code == 422

            # Test with whitespace only - passes Pydantic but fails API validation
            response = test_client.post(
                "/api/shared/empty_msg_token/chat",
                json={"content": "   "}
            )
            # After Pydantic, API validates and strips whitespace
            # Empty after strip returns 400 from API
            assert response.status_code == 400
            assert "不能为空" in response.json()["detail"] or "empty" in response.json()["detail"].lower()
        finally:
            # Clean up rate limit store (testclient IP accumulates)
            from app.core.rate_limit import clear_rate_limit
            clear_rate_limit("testclient")
            clear_rate_limit("127.0.0.1")

            db_session.query(ShareLink).filter(ShareLink.share_token == "empty_msg_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_rate_limiting(self, test_client: TestClient, db_session: Session) -> None:
        """Test rate limiting for shared chat endpoint."""
        # Clear rate limit before test to ensure clean state
        from app.core.rate_limit import clear_rate_limit
        clear_rate_limit("testclient")
        clear_rate_limit("127.0.0.1")

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
            clear_rate_limit("127.0.0.1")
            clear_rate_limit("testclient")

            db_session.query(ShareLink).filter(ShareLink.share_token == "rate_limit_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_valid_request_structure(self, test_client: TestClient, db_session: Session) -> None:
        """Test that valid chat request returns expected response structure."""
        # Clear rate limit before test
        from app.core.rate_limit import clear_rate_limit
        clear_rate_limit("testclient")
        clear_rate_limit("127.0.0.1")

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
            # Clean up rate limit store (testclient IP accumulates)
            clear_rate_limit("testclient")
            clear_rate_limit("127.0.0.1")

            db_session.query(ShareLink).filter(ShareLink.share_token == "valid_chat_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_deleted_transcription_returns_404(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with deleted transcription (orphaned share link) returns 404."""
        # Clear rate limit before test
        from app.core.rate_limit import clear_rate_limit
        clear_rate_limit("testclient")
        clear_rate_limit("127.0.0.1")

        # Create test user and transcription first
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-orphan-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_orphan.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="orphaned_chat_token"
        )
        db_session.add(link)
        db_session.commit()

        # Delete the transcription (simulating orphaned share link)
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.commit()

        try:
            response = test_client.post(
                "/api/shared/orphaned_chat_token/chat",
                json={"content": "Hello"}
            )
            assert response.status_code == 404
            # The API returns generic "不存在" message
            assert "不存在" in response.json()["detail"]
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "orphaned_chat_token").delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_message_too_long_returns_422(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with message exceeding max length returns 422."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-long-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_long.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="long_msg_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Message exceeding max_length (5000 chars)
            long_message = "a" * 5001
            response = test_client.post(
                "/api/shared/long_msg_token/chat",
                json={"content": long_message}
            )
            # Pydantic validation returns 422 for schema violations
            assert response.status_code == 422
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "long_msg_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_missing_content_field_returns_422(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with missing content field returns 422."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-missing-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_missing.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="missing_field_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Missing content field
            response = test_client.post(
                "/api/shared/missing_field_token/chat",
                json={}  # Empty JSON, missing content field
            )
            assert response.status_code == 422
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "missing_field_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_with_special_characters_succeeds(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with special characters and unicode content succeeds."""
        # Create test user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-special-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_special.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.flush()

        # Save transcription text using storage service
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        storage.save_transcription_text(str(tid), "Test transcription with some content.")

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="special_chars_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Test with unicode, emojis, and special characters
            special_message = "Hello! 你好！ 🎉 Test with <special> & \"chars\""
            response = test_client.post(
                "/api/shared/special_chars_token/chat",
                json={"content": special_message}
            )
            # May return 200 or 500 (GLM error), but not 4xx validation errors
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert data["role"] == "assistant"
                assert "content" in data
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "special_chars_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_shared_chat_empty_transcription_text(self, test_client: TestClient, db_session: Session) -> None:
        """Test chat with empty transcription text handles gracefully."""
        # Create test user and transcription with no saved text (empty by default)
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-chat-empty-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_chat_empty_text.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
            # No text saved, so transcription.text property will return empty string
        )
        db_session.add(trans)
        db_session.commit()

        # Create share link
        link = ShareLink(
            id=uuid.uuid4(),
            transcription_id=tid,
            share_token="empty_text_token"
        )
        db_session.add(link)
        db_session.commit()

        try:
            response = test_client.post(
                "/api/shared/empty_text_token/chat",
                json={"content": "What is this about?"}
            )
            # May return 200 or 500 (GLM may fail with empty context), but not 4xx
            assert response.status_code in [200, 500]
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "empty_text_token").delete()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()


@pytest.mark.integration
class TestRateLimitUtility:
    """Test rate limiting utility functions."""

    def test_rate_limit_status_returns_correct_counts(self, test_client: TestClient) -> None:
        """Test get_rate_limit_status returns correct remaining and reset time."""
        from app.core.rate_limit import get_rate_limit_status, clear_rate_limit

        # Clear any existing data
        clear_rate_limit("127.0.0.1")

        try:
            # Initially, should have full limit available
            status = get_rate_limit_status("127.0.0.1")
            assert status["limit"] == 10
            assert status["remaining"] == 10
            assert status["window"] == 60

            # After using some requests
            for _ in range(3):
                from app.core.rate_limit import rate_limit_shared_chat
                rate_limit_shared_chat("127.0.0.1")

            status = get_rate_limit_status("127.0.0.1")
            assert status["limit"] == 10
            assert status["remaining"] == 7
        finally:
            clear_rate_limit("127.0.0.1")

    def test_rate_limit_clear_single_ip(self, test_client: TestClient) -> None:
        """Test clear_rate_limit removes data for specific IP."""
        from app.core.rate_limit import rate_limit_shared_chat, get_rate_limit_status, clear_rate_limit

        # Add some requests
        for _ in range(3):
            rate_limit_shared_chat("192.168.1.1")

        # Verify data exists
        status = get_rate_limit_status("192.168.1.1")
        assert status["remaining"] == 7

        # Clear specific IP
        clear_rate_limit("192.168.1.1")

        # Verify data is cleared
        status = get_rate_limit_status("192.168.1.1")
        assert status["remaining"] == 10

    def test_rate_limit_clear_all_ips(self, test_client: TestClient) -> None:
        """Test clear_rate_limit clears all data when no IP specified."""
        from app.core.rate_limit import rate_limit_shared_chat, get_rate_limit_status, clear_rate_limit

        # Add requests for multiple IPs
        rate_limit_shared_chat("192.168.1.1")
        rate_limit_shared_chat("192.168.1.2")
        rate_limit_shared_chat("192.168.1.3")

        # Verify data exists
        assert get_rate_limit_status("192.168.1.1")["remaining"] == 9
        assert get_rate_limit_status("192.168.1.2")["remaining"] == 9
        assert get_rate_limit_status("192.168.1.3")["remaining"] == 9

        # Clear all
        clear_rate_limit()

        # Verify all cleared
        assert get_rate_limit_status("192.168.1.1")["remaining"] == 10
        assert get_rate_limit_status("192.168.1.2")["remaining"] == 10
        assert get_rate_limit_status("192.168.1.3")["remaining"] == 10

    def test_rate_limit_window_expiration_resets_counter(self, test_client: TestClient) -> None:
        """Test that old entries outside time window are cleaned up."""
        import time
        from app.core.rate_limit import (
            rate_limit_shared_chat,
            get_rate_limit_status,
            clear_rate_limit,
            _rate_limit_store,
            _RATE_LIMIT_WINDOW
        )

        test_ip = "10.0.0.1"
        clear_rate_limit(test_ip)

        try:
            # Add old timestamps outside the window
            now = time.time()
            old_timestamps = [
                now - _RATE_LIMIT_WINDOW - 10,  # Outside window
                now - _RATE_LIMIT_WINDOW - 5,   # Outside window
            ]
            _rate_limit_store[test_ip] = old_timestamps

            # Adding a new request should clean old entries
            rate_limit_shared_chat(test_ip)

            # Should only have 1 request (old ones cleaned)
            status = get_rate_limit_status(test_ip)
            assert status["remaining"] == 9
            assert len(_rate_limit_store[test_ip]) == 1
        finally:
            clear_rate_limit(test_ip)

    def test_rate_limit_multiple_ips_independent(self, test_client: TestClient) -> None:
        """Test that rate limits are tracked independently per IP."""
        from app.core.rate_limit import rate_limit_shared_chat, get_rate_limit_status, clear_rate_limit

        ip1 = "192.168.1.100"
        ip2 = "192.168.1.200"

        clear_rate_limit(ip1)
        clear_rate_limit(ip2)

        try:
            # Use different number of requests for each IP
            for _ in range(5):
                rate_limit_shared_chat(ip1)

            for _ in range(3):
                rate_limit_shared_chat(ip2)

            # Verify independent tracking
            status1 = get_rate_limit_status(ip1)
            status2 = get_rate_limit_status(ip2)

            assert status1["remaining"] == 5  # 10 - 5
            assert status2["remaining"] == 7  # 10 - 3
        finally:
            clear_rate_limit(ip1)
            clear_rate_limit(ip2)
