"""
Transcription Model Missing Coverage Tests

Tests for uncovered property methods in Transcription model.
"""

import pytest
import uuid
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import gzip

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.services.storage_service import get_storage_service


@pytest.mark.integration
class TestTranscriptionModelProperty:
    """Test Transcription model property methods."""

    def test_text_property_with_valid_storage(self, db_session: Session) -> None:
        """text property reads from storage service."""
        # Create user and transcription
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        storage = get_storage_service()

        # Save test text to storage
        test_text = "This is a test transcription text."
        storage.save_transcription_text(str(tid), test_text)

        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=f"{tid}.txt.gz"
        )
        db_session.add(trans)
        db_session.commit()

        # Access text property - should read from storage
        retrieved_text = trans.text
        assert retrieved_text == test_text

        # Cleanup
        storage.delete_transcription_text(str(tid))
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_text_property_with_missing_storage(self, db_session: Session) -> None:
        """text property returns None when storage file doesn't exist."""
        # Create user and transcription without storage
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path=None  # No storage path
        )
        db_session.add(trans)
        db_session.commit()

        # Access text property - should return None or empty string
        retrieved_text = trans.text
        assert retrieved_text is None or retrieved_text == ""

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_text_property_with_invalid_storage_path(self, db_session: Session) -> None:
        """text property handles invalid storage path gracefully."""
        # Create user and transcription with invalid storage
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            storage_path="nonexistent.txt.gz"  # File doesn't exist
        )
        db_session.add(trans)
        db_session.commit()

        # Access text property - should handle gracefully
        retrieved_text = trans.text
        assert retrieved_text is None or retrieved_text == ""

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()
