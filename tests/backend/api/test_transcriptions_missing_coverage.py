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
