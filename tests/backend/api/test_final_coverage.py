"""
Final Coverage Test - Remaining Achievable Missing Lines.

This test targets the last remaining achievable missing lines:
- Line 245-246: DELETE ALL outer exception handler
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.models.transcription import Transcription
from app.models.user import User


@pytest.mark.integration
class TestFinalRemainingCoverage:
    """Test final remaining achievable missing lines."""

    def test_delete_all_outer_exception_hits_line_246(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test DELETE ALL outer exception handler executes line 246.

        This targets transcriptions.py lines 245-246:
        ```python
        except Exception as e:
            logger.error(f"[DELETE ALL] File deletion error for {transcription_id}: {e}")
        ```

        Strategy: Cause an exception during file deletion loop.
        """
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_exception.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path="/fake/path/test.mp3"
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock os.path.exists to raise exception
        with patch('os.path.exists', side_effect=OSError("Disk error")):
            # Call delete all endpoint - should handle exception gracefully
            response = real_auth_client.delete("/api/transcriptions/all")

            # Verify successful deletion despite exception
            assert response.status_code == 200

    def test_delete_all_with_loop_exception_hits_245_246(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test DELETE ALL with loop exception hits lines 245-246.

        This targets the outer exception handler in the for loop.
        """
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_loop_exception.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path="test/transcription.txt.gz",
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock storage service to raise exception during iteration
        with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
            mock_storage = MagicMock()
            # Raise exception on first call, succeed on second (for commit)
            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("Storage error")
                return None
            mock_storage.delete_transcription_text.side_effect = side_effect
            mock_get_storage.return_value = mock_storage

            # Call delete all - should handle exception
            response = real_auth_client.delete("/api/transcriptions/all")

            # Verify successful deletion despite exception
            assert response.status_code == 200
