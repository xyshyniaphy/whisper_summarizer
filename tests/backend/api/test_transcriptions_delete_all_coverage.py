"""
DELETE ALL endpoint coverage test.

This test specifically targets app/api/transcriptions.py lines 203-254.
These lines are in the DELETE ALL endpoint and include:
- The for loop that iterates through transcriptions
- File deletion logic
- Database deletion logic

The existing tests don't cover these lines because they either:
1. Don't create transcriptions before calling delete all (empty list)
2. Use mocks that don't execute the real code path

This test uses real database sessions and creates transcriptions to ensure
the for loop body executes.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from app.models.transcription import Transcription
from app.models.user import User


@pytest.mark.integration
class TestDeleteAllCoverage:
    """Test DELETE ALL endpoint coverage for lines 203-254."""

    def test_delete_all_with_transcriptions_hits_loop_body(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with existing transcriptions executes lines 203-254.

        This targets transcriptions.py lines 203-254:
        - Line 203: deleted_count = 0
        - Lines 206-254: The for loop body that processes each transcription

        Strategy:
        1. Create real transcriptions in the database
        2. Call DELETE /api/transcriptions/all
        3. Verify the loop executed and deleted the transcriptions
        """
        # Get user from database
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create multiple transcriptions for this user
        # Note: text is a read-only property, so we don't set it
        transcription_count = 3
        transcriptions = []
        for i in range(transcription_count):
            transcription = Transcription(
                id=uuid4(),
                user_id=user.id,
                file_name=f"test_audio_{i}.mp3",
                status="completed",
                language="zh",
                duration_seconds=120 + i * 10,
                created_at=datetime.now(timezone.utc),
                storage_path=None,  # No storage to avoid Supabase dependency
                file_path=None  # No file path
            )
            db_session.add(transcription)
            transcriptions.append(transcription)

        db_session.commit()

        # Verify transcriptions exist
        transcriptions_before = db_session.query(Transcription).filter(
            Transcription.user_id == user.id
        ).count()
        assert transcriptions_before == transcription_count

        # Call delete all endpoint
        # This executes lines 203-254:
        # - Line 203: deleted_count = 0
        # - Lines 206-254: for loop processes each transcription
        response = real_auth_client.delete("/api/transcriptions/all")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert data["deleted_count"] == transcription_count

        # Verify transcriptions were deleted
        transcriptions_after = db_session.query(Transcription).filter(
            Transcription.user_id == user.id
        ).count()
        assert transcriptions_after == 0

    def test_delete_all_empty_hits_line_203(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with no transcriptions hits line 203 and early return.

        This targets transcriptions.py lines 200-201:
        ```python
        if not transcriptions:
            return {"deleted_count": 0, "message": "削除する項目がありません"}
        ```
        """
        # Ensure no transcriptions exist
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Delete any existing transcriptions
        db_session.query(Transcription).filter(
            Transcription.user_id == user.id
        ).delete()
        db_session.commit()

        # Call delete all endpoint
        response = real_auth_client.delete("/api/transcriptions/all")

        # Verify early return response
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        assert "項目がありません" in data.get("message", "")

    def test_delete_all_with_storage_path_hits_storage_deletion(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with storage_path hits storage deletion code.

        This targets transcriptions.py lines 222-232 which delete from storage.
        """
        from unittest.mock import patch, MagicMock

        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription with storage_path
        # Note: text is a read-only property, so we don't set it
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_with_storage.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path="test/transcription.txt.gz",  # Has storage path
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock storage service to avoid actual Supabase calls
        with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage

            # Call delete all endpoint
            response = real_auth_client.delete("/api/transcriptions/all")

            # Verify storage deletion was called
            assert mock_storage.delete_transcription_text.called
            assert response.status_code == 200

    def test_delete_all_with_file_path_hits_line_235(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with file_path executes line 235.

        This targets transcriptions.py line 235:
        ```python
        os.remove(transcription.file_path)
        ```

        Strategy: Create transcription with file_path and mock os.remove.
        """
        from unittest.mock import patch

        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription with file_path
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_with_file_path.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path="/fake/path/test.mp3"  # Fake file path
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock os.path.exists and os.remove
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                # Call delete all endpoint
                response = real_auth_client.delete("/api/transcriptions/all")

                # Verify os.remove was called (line 235)
                assert mock_remove.called
                assert response.status_code == 200

    def test_delete_all_with_output_files_hits_line_240(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with output files executes line 240.

        This targets transcriptions.py line 240:
        ```python
        output_file.unlink()
        ```

        Strategy: Create output files and delete all transcriptions.
        """
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_with_output.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Create output files
        output_dir = Path("/app/data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{transcription.id}.txt"
        output_file.write_text("Test content")

        # Call delete all endpoint
        response = real_auth_client.delete("/api/transcriptions/all")

        # Verify successful deletion and file removal
        assert response.status_code == 200
        assert not output_file.exists()

    def test_delete_all_with_converted_wav_hits_line_244(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with converted wav executes line 244.

        This targets transcriptions.py line 244:
        ```python
        converted_wav.unlink()
        ```

        Strategy: Create converted wav file and delete all transcriptions.
        """
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_converted.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Create converted wav file
        output_dir = Path("/app/data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        converted_wav = output_dir / f"{transcription.id}_converted.wav"
        converted_wav.write_bytes(b"RIFF" + b"\x00" * 100)

        # Call delete all endpoint
        response = real_auth_client.delete("/api/transcriptions/all")

        # Verify successful deletion and file removal
        assert response.status_code == 200
        assert not converted_wav.exists()

    def test_delete_all_storage_exception_hits_line_232(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete all with storage exception executes line 232.

        This targets transcriptions.py lines 231-232:
        ```python
        except Exception as e:
            logger.warning(f"[DELETE ALL] Failed to delete from storage: {e}")
        ```

        Strategy: Mock storage service to raise exception.
        """
        from unittest.mock import patch, MagicMock

        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription with storage_path
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_storage_exception.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path="test/transcription.txt.gz",
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock storage service to raise exception
        with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.delete_transcription_text.side_effect = Exception("Storage error")
            mock_get_storage.return_value = mock_storage

            # Delete should succeed despite storage error
            response = real_auth_client.delete("/api/transcriptions/all")

            # Verify successful deletion (error is logged but doesn't fail)
            assert response.status_code == 200
