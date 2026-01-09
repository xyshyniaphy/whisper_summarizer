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

    def test_original_text_property_returns_empty_without_storage_path(self, db_session: Session) -> None:
        """original_text property returns empty string when storage_path is None."""
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

        # original_text should return empty string
        retrieved_text = trans.original_text
        assert retrieved_text == ""

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_original_text_property_returns_text_from_storage(self, db_session: Session) -> None:
        """original_text property reads from storage service."""
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        storage = get_storage_service()

        # Save test text to storage
        test_text = "Original transcription text without formatting."
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

        # original_text should read from storage
        retrieved_text = trans.original_text
        assert retrieved_text == test_text

        # Cleanup
        storage.delete_transcription_text(str(tid))
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_time_remaining_property_for_recent_transcription(self, db_session: Session) -> None:
        """time_remaining property returns positive timedelta for recent transcriptions."""
        from datetime import timedelta

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
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # For a just-created transcription, time_remaining should be positive (close to MAX_KEEP_DAYS)
        remaining = trans.time_remaining
        assert remaining.total_seconds() > 0
        # Should be approximately MAX_KEEP_DAYS (default 7 days = 604800 seconds)
        assert remaining.total_seconds() > 600000  # Allow some margin

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_is_expired_property_for_recent_transcription(self, db_session: Session) -> None:
        """is_expired property returns False for recent transcriptions."""
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
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        # For a just-created transcription, is_expired should be False
        assert trans.is_expired is False

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_processing_time_property_with_started_and_completed(self, db_session: Session) -> None:
        """processing_time property returns duration when started_at and completed_at are set."""
        from datetime import datetime, timezone, timedelta

        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        started = datetime.now(timezone.utc) - timedelta(seconds=100)
        completed = datetime.now(timezone.utc) - timedelta(seconds=50)

        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed",
            started_at=started,
            completed_at=completed
        )
        db_session.add(trans)
        db_session.commit()

        # processing_time should return approximately 50 seconds
        proc_time = trans.processing_time
        assert proc_time is not None
        assert 45 <= proc_time <= 55  # Allow some margin for timing

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_processing_time_property_falls_back_to_processing_time_seconds(self, db_session: Session) -> None:
        """processing_time property returns processing_time_seconds when timestamps not available."""
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
            started_at=None,
            completed_at=None,
            processing_time_seconds=123
        )
        db_session.add(trans)
        db_session.commit()

        # processing_time should return processing_time_seconds value
        assert trans.processing_time == 123

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()

    def test_processing_time_property_returns_none_when_not_available(self, db_session: Session) -> None:
        """processing_time property returns None when no timing data is available."""
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.commit()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test.mp3",
            status=TranscriptionStatus.PENDING,
            stage="uploading",
            started_at=None,
            completed_at=None,
            processing_time_seconds=None
        )
        db_session.add(trans)
        db_session.commit()

        # processing_time should return None
        assert trans.processing_time is None

        # Cleanup
        db_session.query(Transcription).filter(Transcription.id == tid).delete()
        db_session.query(User).filter(User.id == uid).delete()
        db_session.commit()
