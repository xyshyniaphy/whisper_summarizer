"""
Transcription Model Error Path Tests

Tests for uncovered error handling paths in transcription model properties.
"""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestTranscriptionModelPropertyErrorPaths:
    """Test transcription model property error handling."""

    def test_original_text_storage_error_returns_empty_string(self, db_session: Session) -> None:
        """Test original_text property handles storage errors gracefully."""
        from app.models.transcription import Transcription, TranscriptionStatus
        from app.models.user import User

        # Create user
        uid = uuid4()
        user = User(id=uid, email=f"storage-error-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription with storage path that will cause error
        tid = uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="storage-error.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=f"{tid}.txt.gz"  # File doesn't exist
        )
        db_session.add(trans)
        db_session.commit()

        # Access original_text - should handle error and return empty string
        result = trans.original_text
        assert result == ""

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_original_text_with_none_storage_path(self, db_session: Session) -> None:
        """Test original_text returns empty string when storage_path is None."""
        from app.models.transcription import Transcription, TranscriptionStatus
        from app.models.user import User

        # Create user
        uid = uuid4()
        user = User(id=uid, email=f"none-storage-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create transcription without storage path
        tid = uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="no-storage.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=None
        )
        db_session.add(trans)
        db_session.commit()

        # Access original_text - should return empty string
        result = trans.original_text
        assert result == ""

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()
