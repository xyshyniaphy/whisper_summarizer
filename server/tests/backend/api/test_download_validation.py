"""
Transcription Download Validation Tests

Test for transcriptions.py lines 391-392 - invalid UUID format handling.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus


@pytest.fixture
def regular_user(db_session: Session) -> dict:
    """Create regular user for download tests."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"download-test-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def auth_client_for_download(regular_user: dict, db_session: Session) -> TestClient:
    """Authenticated test client for download validation tests."""
    from app.main import app
    from app.core.supabase import get_current_user

    async def override_auth():
        return {
            "id": regular_user["id"],
            "email": regular_user["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": False, "is_active": True}
        }

    app.dependency_overrides[get_current_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestTranscriptionDownloadValidation:
    """Test transcription download validation."""

    def test_download_transcription_with_invalid_uuid_hits_line_391_392(
        self,
        auth_client_for_download: TestClient,
        db_session: Session
    ) -> None:
        """
        Download with invalid UUID format.

        This targets transcriptions.py lines 391-392:
        ```python
        try:
            transcription_uuid = UUID(transcription_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid transcription ID format")
        ```
        """
        # Test various invalid UUID formats (non-empty strings)
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "abcdef",
            "uuid-123-456",
            "00000000-0000-0000-0000-00000000000G",  # Invalid character
        ]

        for invalid_id in invalid_uuids:
            response = auth_client_for_download.get(
                f"/api/transcriptions/{invalid_id}/download"
            )

            # Should return 422 for invalid UUID format
            assert response.status_code == 422, f"Expected 422 for {invalid_id}, got {response.status_code}"
            detail = response.json()["detail"]
            assert "invalid" in detail.lower() or "format" in detail.lower()

        # Empty string returns 404 at routing level (before our code)
        response = auth_client_for_download.get("/api/transcriptions//download")
        assert response.status_code == 404

    def test_download_transcription_with_valid_format_but_nonexistent_id(
        self,
        auth_client_for_download: TestClient,
        db_session: Session
    ) -> None:
        """
        Download with valid UUID format but non-existent ID.

        This tests the 404 path after UUID validation passes.
        """
        # Valid UUID format but doesn't exist
        fake_id = str(uuid.uuid4())

        response = auth_client_for_download.get(
            f"/api/transcriptions/{fake_id}/download"
        )

        # Should return 404 for non-existent transcription
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "未找到" in detail or "not found" in detail.lower()
