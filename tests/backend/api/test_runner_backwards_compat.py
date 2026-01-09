"""
Runner API Backwards Compatibility Tests

Test for runner.py line 303 - storage_path backwards compatibility.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.core.supabase import get_current_user
from app.main import app


@pytest.fixture
def test_user_with_transcription(db_session: Session):
    """Create a test user with a transcription."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"runner-compat-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def runner_auth_client(test_user_with_transcription: User) -> TestClient:
    """Authenticated test client for runner API."""
    from app.core.config import settings

    async def override_auth():
        return {
            "id": str(test_user_with_transcription.id),
            "email": test_user_with_transcription.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    from app.core.supabase import get_current_user
    app.dependency_overrides[get_current_user] = override_auth

    with TestClient(app) as client:
        # Set runner API key header
        client.headers["Authorization"] = f"Bearer {settings.RUNNER_API_KEY}"
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestRunnerBackwardsCompatibility:
    """Test runner API backwards compatibility for storage_path."""

    def test_get_audio_uses_storage_path_when_file_path_missing_hits_line_303(
        self,
        runner_auth_client: TestClient,
        test_user_with_transcription: User,
        db_session: Session
    ) -> None:
        """
        Test that storage_path is used as fallback when file_path is not set.

        This targets runner.py line 303:
        ```python
        file_path = job.storage_path
        ```

        This tests backwards compatibility for jobs that only have storage_path set.
        """
        # Create transcription with storage_path but NO file_path
        tid = uuid.uuid4()
        uid = test_user_with_transcription.id

        # Create a temporary audio file
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        test_file = temp_dir / f"test_storage_path_{tid}.mp3"
        test_file.write_bytes(b"fake audio content")

        # Create transcription with storage_path set (old format)
        transcription = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_storage_path.mp3",
            storage_path=str(test_file),  # Set storage_path (old format)
            file_path=None,  # No file_path (new format)
            status=TranscriptionStatus.PROCESSING,
            runner_id="test-runner",
            stage="processing"
        )
        db_session.add(transcription)
        db_session.commit()

        try:
            # Request audio file - should fall back to storage_path (line 303)
            response = runner_auth_client.get(f"/api/runner/audio/{tid}")

            # Should return the file path
            assert response.status_code == 200
            data = response.json()
            assert data["file_path"] == str(test_file)

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()
