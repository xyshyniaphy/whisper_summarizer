"""
Transcription Model Storage Exception Tests

Tests for transcription.py storage exception handlers:
- Lines 74-77: original_text property storage exception
- Lines 97-100: text property storage exception
"""

import pytest
import uuid
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User


@pytest.mark.integration
class TestTranscriptionStorageExceptions:
    """Test transcription model storage exception handlers."""

    def test_original_text_storage_exception_hits_lines_74_77(
        self,
        db_session: Session
    ) -> None:
        """
        Test that storage exceptions in original_text are handled gracefully.

        This targets transcription.py lines 74-77:
        ```python
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load original transcription text from storage: {e}")
            return ""
        ```

        Scenario:
        1. Create transcription with storage_path set
        2. Mock storage service to raise exception
        3. Access original_text property
        4. Should catch exception and return empty string (lines 74-77)
        """
        # Create user
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-storage-exception-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription with storage_path set
        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_storage_exception.mp3",
            storage_path="/fake/path/to/storage.txt",  # Has storage_path
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Mock storage service to raise exception
            # Patch at the source since it's imported locally in the property
            with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage
                mock_storage.get_transcription_text.side_effect = Exception("Storage service unavailable!")

                # Access original_text property - should handle exception
                result = trans.original_text

                # Should return empty string (line 77)
                assert result == ""

        finally:
            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_text_property_storage_exception_hits_lines_97_100(
        self,
        db_session: Session
    ) -> None:
        """
        Test that storage exceptions in text property are handled gracefully.

        This targets transcription.py lines 97-100:
        ```python
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load transcription text from storage: {e}")
            return ""
        ```

        Scenario:
        1. Create transcription
        2. Mock storage service to raise exception
        3. Access text property
        4. Should catch exception and return empty string (lines 97-100)
        """
        # Create user
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-text-exception-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription (no storage_path needed for this test)
        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_text_exception.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Mock storage service to raise exception
            # Patch at the source since it's imported locally in the property
            with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage
                # formatted_text_exists returns False, then get_transcription_text raises exception
                mock_storage.formatted_text_exists.return_value = False
                mock_storage.get_transcription_text.side_effect = Exception("Storage failure!")

                # Access text property - should handle exception
                result = trans.text

                # Should return empty string (line 100)
                assert result == ""

        finally:
            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_text_property_formatted_text_exception_hits_lines_97_100(
        self,
        db_session: Session
    ) -> None:
        """
        Test that formatted text storage exceptions are handled gracefully.

        This targets transcription.py lines 97-100 when formatted_text_exists
        returns True but get_formatted_text raises exception.

        Scenario:
        1. Create transcription
        2. Mock storage service to raise exception when getting formatted text
        3. Access text property
        4. Should catch exception and return empty string (lines 97-100)
        """
        # Create user
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-formatted-exception-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription
        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_formatted_exception.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Mock storage service - formatted text exists but raises exception
            # Patch at the source since it's imported locally in the property
            with patch('app.services.storage_service.get_storage_service') as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage
                # formatted_text_exists returns True, then get_formatted_text raises exception
                mock_storage.formatted_text_exists.return_value = True
                mock_storage.get_formatted_text.side_effect = Exception("Formatted text storage failure!")

                # Access text property - should handle exception
                result = trans.text

                # Should return empty string (line 100)
                assert result == ""

        finally:
            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()

    def test_original_text_no_storage_path_returns_empty(
        self,
        db_session: Session
    ) -> None:
        """
        Test that original_text returns empty string when no storage_path.

        This targets transcription.py line 67-68:
        ```python
        if not self.storage_path:
            return ""
        ```

        Scenario:
        1. Create transcription without storage_path
        2. Access original_text property
        3. Should return empty string without accessing storage (lines 67-68)
        """
        # Create user
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-no-storage-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription WITHOUT storage_path
        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_no_storage.mp3",
            storage_path=None,  # No storage_path
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Access original_text property - should return empty without accessing storage
            result = trans.original_text

            # Should return empty string (line 68)
            assert result == ""

        finally:
            # Cleanup
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()
