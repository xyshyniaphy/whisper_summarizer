"""
Transcriptions API Missing Lines Coverage Test.

This test targets achievable missing lines in app/api/transcriptions.py:
- Line 87: Admin path in transcriptions list
- Line 122: Channel filter in transcriptions list
- Line 433: Empty transcription content error
- Line 1084: Channels not found error
- Lines 333-334, 346-347, 352-353, 355-358: Exception handlers and file checks
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from app.models.transcription import Transcription
from app.models.user import User
from app.models.channel import Channel, ChannelMembership


@pytest.mark.integration
class TestTranscriptionsMissingCoverage:
    """Test transcriptions API missing lines."""

    def test_admin_transcriptions_list_hits_line_87(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test admin transcriptions list executes line 87.

        This targets transcriptions.py line 87:
        ```python
        query = db.query(Transcription)  # Admin sees everything
        ```

        Strategy: Make user admin and call list endpoint.
        """
        # Make user admin
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None
        user.is_admin = True
        db_session.commit()

        # Create test transcription for this user
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_admin.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Call list endpoint - admin path
        # Note: real_auth_client should pick up admin status on next request
        response = real_auth_client.get("/api/transcriptions?page=1&page_size=10")

        # Verify response - admin path executes line 87
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_delete_with_storage_exception_hits_lines_333_334(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete with storage exception executes lines 333-334.

        This targets transcriptions.py lines 333-334:
        ```python
        except Exception as e:
            logger.warning(f"[DELETE] Failed to delete from storage: {e}")
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
            response = real_auth_client.delete(f"/api/transcriptions/{transcription.id}")

            # Verify successful deletion (error is logged but doesn't fail)
            assert response.status_code == 204

    def test_delete_with_file_hits_lines_346_347(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete with output file executes lines 346-347.

        This targets transcriptions.py lines 346-347:
        ```python
        if output_file.exists():
            output_file.unlink()
        ```

        Strategy: Create output file and delete transcription.
        """
        user = db_session.query(User).filter(
            User.email == real_auth_user["email"]
        ).first()
        assert user is not None

        # Create transcription
        transcription = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name="test_with_file.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path=None
        )
        db_session.add(transcription)
        db_session.commit()

        # Create output file
        output_dir = Path("/app/data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{transcription.id}.txt"
        output_file.write_text("Test transcription content")

        # Delete transcription
        response = real_auth_client.delete(f"/api/transcriptions/{transcription.id}")

        # Verify successful deletion and file removal
        assert response.status_code == 204
        assert not output_file.exists()

    def test_delete_with_converted_wav_hits_lines_352_353(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete with converted wav executes lines 352-353.

        This targets transcriptions.py lines 352-353:
        ```python
        if converted_wav.exists():
            converted_wav.unlink()
        ```

        Strategy: Create converted wav file and delete transcription.
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

        # Delete transcription
        response = real_auth_client.delete(f"/api/transcriptions/{transcription.id}")

        # Verify successful deletion and file removal
        assert response.status_code == 204
        assert not converted_wav.exists()

    def test_delete_outer_exception_handler_hits_lines_355_358(
        self,
        real_auth_client: TestClient,
        db_session: Session,
        real_auth_user: dict
    ) -> None:
        """
        Test delete outer exception handler executes lines 355-358.

        This targets transcriptions.py lines 355-358:
        ```python
        except Exception as e:
            logger.error(f"ファイル削除エラー: {e}")
            pass  # DB削除は続行する
        ```

        Strategy: Mock os.remove to raise exception.
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
            file_name="test_exception.mp3",
            status="completed",
            language="zh",
            duration_seconds=120,
            created_at=datetime.now(timezone.utc),
            storage_path=None,
            file_path="/fake/path/test.mp3"  # Fake path that will cause error
        )
        db_session.add(transcription)
        db_session.commit()

        # Mock os.path.exists to return True and os.remove to raise exception
        with patch('os.path.exists', return_value=True):
            with patch('os.remove', side_effect=OSError("Permission denied")):
                # Delete should succeed despite file deletion error
                response = real_auth_client.delete(f"/api/transcriptions/{transcription.id}")

                # Verify successful deletion (error is logged but DB deletion continues)
                assert response.status_code == 204
