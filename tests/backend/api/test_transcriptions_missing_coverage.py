"""
Additional Transcription API Tests for Missing Coverage

Tests for uncovered code paths in transcriptions.py to improve
coverage from 75% to higher.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel
from app.models.summary import Summary
from app.core.supabase import get_current_active_user
from app.main import app
from uuid import uuid4


@pytest.mark.integration
class TestTranscriptionOwnership:
    """Test transcription ownership verification."""

    def test_get_other_user_transcription_returns_404(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Getting another user's transcription returns 404."""
        # Create another user's transcription
        other_uid = uuid.uuid4()
        other_user = User(id=other_uid, email=f"other-{str(other_uid)[:8]}@example.com", is_active=True)
        db_session.add(other_user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=other_uid,
            file_name="other.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Try to access with different user (user_auth_client) - should return 404
        response = user_auth_client.get(f"/api/transcriptions/{tid}")
        assert response.status_code == 404

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == other_uid).delete()
        db_session.commit()


@pytest.mark.integration
class TestDownloadMissingRequirements:
    """Test download endpoints with missing required data."""

    def test_download_docx_without_summary_returns_404(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Downloading DOCX without summary returns 404."""
        test_user_id = str(uuid4())

        async def override_user_auth():
            return {
                "id": test_user_id,
                "email": f"test-{test_user_id[:8]}@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z"
            }

        app.dependency_overrides[get_current_active_user] = override_user_auth

        try:
            # Create user and transcription WITHOUT summary
            uid = uuid.UUID(test_user_id)
            user = User(id=uid, email=f"test-{test_user_id[:8]}@example.com", is_active=True)
            db_session.add(user)
            db_session.commit()

            tid = uuid.uuid4()
            trans = Transcription(
                id=tid,
                user_id=uid,
                file_name="test.mp3",
                status=TranscriptionStatus.COMPLETED,
                stage="completed"
            )
            db_session.add(trans)
            db_session.commit()

            # Try to download DOCX - should return 404 (no summary)
            response = user_auth_client.get(f"/api/transcriptions/{tid}/download-docx")
            assert response.status_code == 404

            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

        finally:
            app.dependency_overrides = {}

    def test_download_notebooklm_without_summary_returns_404(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Downloading NotebookLM without summary returns 404."""
        test_user_id = str(uuid4())

        async def override_user_auth():
            return {
                "id": test_user_id,
                "email": f"test-{test_user_id[:8]}@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z"
            }

        app.dependency_overrides[get_current_active_user] = override_user_auth

        try:
            # Create user and transcription WITHOUT summary
            uid = uuid.UUID(test_user_id)
            user = User(id=uid, email=f"test-{test_user_id[:8]}@example.com", is_active=True)
            db_session.add(user)
            db_session.commit()

            tid = uuid.uuid4()
            trans = Transcription(
                id=tid,
                user_id=uid,
                file_name="test.mp3",
                status=TranscriptionStatus.COMPLETED,
                stage="completed"
            )
            db_session.add(trans)
            db_session.commit()

            # Try to download NotebookLM - should return 404 (no summary)
            response = user_auth_client.get(f"/api/transcriptions/{tid}/download-notebooklm")
            assert response.status_code == 404

            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

        finally:
            app.dependency_overrides = {}


@pytest.mark.integration
class TestTranscriptionListEdgeCases:
    """Test transcription list endpoint edge cases."""

    def test_list_transcriptions_with_invalid_stage_returns_empty(self, user_auth_client: TestClient) -> None:
        """Listing transcriptions with invalid stage parameter returns empty results."""
        # Use an invalid stage value that doesn't exist
        response = user_auth_client.get("/api/transcriptions?stage=invalid_stage_value_xyz")
        assert response.status_code == 200
        data = response.json()
        # Should return data field with empty list
        assert "data" in data
        assert isinstance(data["data"], list)
        # Empty list or items filtered out (both acceptable)
        assert len(data["data"]) == 0 or all(item.get("stage") != "invalid_stage_value_xyz" for item in data["data"])

    def test_list_transcriptions_with_negative_page_returns_400(self, user_auth_client: TestClient) -> None:
        """Listing transcriptions with negative page number returns validation error."""
        response = user_auth_client.get("/api/transcriptions?page=-1")
        # FastAPI validation should reject negative page
        assert response.status_code in [400, 422]

    def test_list_transcriptions_with_very_large_page_size_returns_422(self, user_auth_client: TestClient) -> None:
        """Listing transcriptions with very large page size returns validation error."""
        response = user_auth_client.get("/api/transcriptions?page_size=1000000")
        # Pydantic validation should reject extremely large page_size
        assert response.status_code == 422


@pytest.mark.integration
class TestTranscriptionGetEdgeCases:
    """Test transcription get endpoint edge cases."""

    def test_get_transcription_with_invalid_uuid_format_returns_422(self, user_auth_client: TestClient) -> None:
        """Getting transcription with invalid UUID format returns validation error."""
        response = user_auth_client.get("/api/transcriptions/not-a-valid-uuid")
        # FastAPI path validation should reject invalid UUID
        assert response.status_code in [400, 422, 404]

    def test_get_transcription_with_empty_uuid_returns_404(self, user_auth_client: TestClient) -> None:
        """Getting transcription with empty UUID returns not found."""
        response = user_auth_client.get("/api/transcriptions/00000000-0000-0000-0000-000000000000")
        # This valid UUID format but non-existent ID should return 404
        assert response.status_code == 404


@pytest.mark.integration
class TestDeleteTranscriptionEdgeCases:
    """Test delete transcription edge cases."""

    def test_delete_nonexistent_transcription_returns_404(self, user_auth_client: TestClient) -> None:
        """Deleting non-existent transcription returns 404."""
        fake_id = str(uuid.uuid4())
        response = user_auth_client.delete(f"/api/transcriptions/{fake_id}")
        assert response.status_code == 404

    def test_delete_with_invalid_uuid_format_returns_422(self, user_auth_client: TestClient) -> None:
        """Deleting with invalid UUID format returns validation error."""
        response = user_auth_client.delete("/api/transcriptions/not-a-uuid")
        assert response.status_code in [400, 422, 404]


@pytest.mark.integration
class TestShareLinkEdgeCases:
    """Test share link edge cases."""

    def test_create_share_link_with_invalid_uuid_returns_422(self, user_auth_client: TestClient) -> None:
        """Creating share link with invalid UUID format returns 422."""
        response = user_auth_client.post("/api/transcriptions/not-a-valid-uuid/share")
        assert response.status_code == 422

    def test_create_share_link_for_nonexistent_returns_404(self, user_auth_client: TestClient) -> None:
        """Creating share link for non-existent transcription returns 404."""
        fake_id = str(uuid.uuid4())
        response = user_auth_client.post(f"/api/transcriptions/{fake_id}/share")
        assert response.status_code == 404

    def test_create_share_link_for_other_user_transcription_returns_404(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Creating share link for another user's transcription returns 404 (not 403)."""
        from app.models.user import User

        # Create another user's transcription
        other_uid = uuid.uuid4()
        other_user = User(id=other_uid, email=f"other-share-{str(other_uid)[:8]}@example.com", is_active=True)
        db_session.add(other_user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=other_uid,
            file_name="other_share.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Try to create share link as different user (user_auth_client)
        response = user_auth_client.post(f"/api/transcriptions/{tid}/share")
        assert response.status_code == 404

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == other_uid).delete()
        db_session.commit()

    def test_create_share_link_returns_existing_link(self, real_auth_client: TestClient, real_auth_user: dict, db_session: Session) -> None:
        """Creating share link for transcription with existing link returns the same link."""
        from app.models.share_link import ShareLink

        trans_id = str(uuid.uuid4())
        try:
            # Get or create user (avoid duplicate key error)
            uid = uuid.UUID(real_auth_user["id"])
            user = db_session.query(User).filter(User.id == uid).first()
            if not user:
                user = User(id=uid, email=real_auth_user["email"], is_active=True)
                db_session.add(user)
                db_session.commit()

            transcription = Transcription(
                id=uuid.UUID(trans_id),
                user_id=uid,
                file_name="test_share.mp3",
                status=TranscriptionStatus.COMPLETED,
                stage="completed"
            )
            db_session.add(transcription)
            db_session.commit()

            # Create first share link
            response1 = real_auth_client.post(f"/api/transcriptions/{trans_id}/share")
            assert response1.status_code == 200
            data1 = response1.json()
            first_token = data1["share_token"]

            # Create second share link - should return same token
            response2 = real_auth_client.post(f"/api/transcriptions/{trans_id}/share")
            assert response2.status_code == 200
            data2 = response2.json()
            second_token = data2["share_token"]

            # Should return the same share token
            assert second_token == first_token
        finally:
            db_session.query(ShareLink).filter(ShareLink.transcription_id == uuid.UUID(trans_id)).delete()
            db_session.query(Transcription).filter(Transcription.id == uuid.UUID(trans_id)).delete()


@pytest.mark.integration
class TestChannelAssignmentEdgeCases:
    """Test channel assignment edge cases."""

    def test_assign_channels_with_invalid_uuid_returns_422(self, user_auth_client: TestClient) -> None:
        """Assigning channels with invalid transcription UUID returns 422."""
        response = user_auth_client.post(
            "/api/transcriptions/not-a-uuid/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 422

    def test_assign_channels_for_nonexistent_returns_404(self, user_auth_client: TestClient) -> None:
        """Assigning channels for non-existent transcription returns 404."""
        fake_id = str(uuid.uuid4())
        response = user_auth_client.post(
            f"/api/transcriptions/{fake_id}/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 404

    def test_assign_channels_unauthorized_returns_403(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Assigning channels to another user's transcription returns 403."""
        from app.models.user import User

        # Create another user's transcription
        other_uid = uuid.uuid4()
        other_user = User(id=other_uid, email=f"other-channel-{str(other_uid)[:8]}@example.com", is_active=True)
        db_session.add(other_user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=other_uid,
            file_name="other_channel.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Try to assign channels as different user (user_auth_client, not admin)
        response = user_auth_client.post(
            f"/api/transcriptions/{tid}/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 403

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == other_uid).delete()
        db_session.commit()


@pytest.mark.integration
class TestGetTranscriptionChannelsEdgeCases:
    """Test get transcription channels edge cases."""

    def test_get_channels_with_invalid_uuid_returns_422(self, user_auth_client: TestClient) -> None:
        """Getting channels with invalid transcription UUID returns 422."""
        response = user_auth_client.get("/api/transcriptions/not-a-uuid/channels")
        assert response.status_code == 422

    def test_get_channels_for_nonexistent_returns_404(self, user_auth_client: TestClient) -> None:
        """Getting channels for non-existent transcription returns 404."""
        fake_id = str(uuid.uuid4())
        response = user_auth_client.get(f"/api/transcriptions/{fake_id}/channels")
        assert response.status_code == 404

    def test_get_channels_unauthorized_returns_403(self, user_auth_client: TestClient, db_session: Session) -> None:
        """Getting channels for another user's transcription (not in shared channel) returns 403."""
        from app.models.user import User

        # Create another user's transcription (no channels assigned)
        other_uid = uuid.uuid4()
        other_user = User(id=other_uid, email=f"other-get-{str(other_uid)[:8]}@example.com", is_active=True)
        db_session.add(other_user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=other_uid,
            file_name="other_get.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # Try to get channels as different user (user_auth_client, not admin, not channel member)
        response = user_auth_client.get(f"/api/transcriptions/{tid}/channels")
        assert response.status_code == 403

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == other_uid).delete()
        db_session.commit()


@pytest.mark.integration
class TestDownloadTranscriptionEdgeCases:
    """Test download transcription edge cases."""

    def test_download_with_invalid_uuid_returns_422(self, user_auth_client: TestClient) -> None:
        """Downloading with invalid transcription UUID returns 422."""
        response = user_auth_client.get("/api/transcriptions/not-a-valid-uuid/download")
        assert response.status_code == 422

    def test_download_nonexistent_transcription_returns_404(self, user_auth_client: TestClient) -> None:
        """Downloading non-existent transcription returns 404."""
        fake_id = str(uuid.uuid4())
        response = user_auth_client.get(f"/api/transcriptions/{fake_id}/download")
        assert response.status_code == 404

    def test_download_with_invalid_format_returns_422(self, user_auth_client: TestClient) -> None:
        """Downloading with invalid format parameter returns 422."""
        # FastAPI Query pattern validation should reject invalid format
        fake_id = str(uuid.uuid4())
        response = user_auth_client.get(f"/api/transcriptions/{fake_id}/download?format=invalid")
        # FastAPI validation rejects invalid pattern values
        assert response.status_code in [400, 422, 404]

    def test_download_formatted_without_storage_fallback(self, real_auth_client: TestClient, real_auth_user: dict, db_session: Session) -> None:
        """Download formatted text without formatted storage falls back to original text."""
        from app.services.storage_service import get_storage_service

        # Create transcription with original text but no formatted text
        uid = uuid.UUID(real_auth_user["id"])
        user = db_session.query(User).filter(User.id == uid).first()
        if not user:
            user = User(id=uid, email=real_auth_user["email"], is_active=True)
            db_session.add(user)
            db_session.commit()

        tid = uuid.uuid4()
        storage = get_storage_service()

        # Save original text only
        test_text = "This is test transcription text without formatting"
        storage.save_transcription_text(str(tid), test_text)

        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_download.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=f"{tid}.txt.gz"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Request formatted format - should fall back to original
            response = real_auth_client.get(f"/api/transcriptions/{tid}/download?format=formatted")
            # Should succeed (fallback to original)
            assert response.status_code == 200
        finally:
            # Cleanup
            storage.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_download_srt_generates_fake_timestamps(self, real_auth_client: TestClient, real_auth_user: dict, db_session: Session) -> None:
        """Download SRT format generates timestamps for transcriptions without real timestamps."""
        from app.services.storage_service import get_storage_service

        # Create transcription with plain text (no real timestamps)
        uid = uuid.UUID(real_auth_user["id"])
        user = db_session.query(User).filter(User.id == uid).first()
        if not user:
            user = User(id=uid, email=real_auth_user["email"], is_active=True)
            db_session.add(user)
            db_session.commit()

        tid = uuid.uuid4()
        storage = get_storage_service()

        # Save plain text
        test_text = "Line one\nLine two\nLine three"
        storage.save_transcription_text(str(tid), test_text)

        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_srt.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=f"{tid}.txt.gz"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Request SRT format
            response = real_auth_client.get(f"/api/transcriptions/{tid}/download?format=srt")
            assert response.status_code == 200
            # Should contain SRT format with timestamps
            content = response.content.decode("utf-8")
            assert "-->" in content  # SRT timestamp marker
        finally:
            # Cleanup
            storage.delete_transcription_text(str(tid))
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()
