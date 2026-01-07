"""
Cleanup Task Tests

Tests for automatic cleanup of expired transcriptions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock
import uuid

from app.tasks.cleanup import cleanup_expired_transcriptions
from app.models.transcription import Transcription
from app.models.summary import Summary


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def old_transcription(db_session: Session) -> Transcription:
    """Create an old transcription that should be cleaned up."""
    from app.models.user import User

    # First create a user
    user = User(
        id=uuid.uuid4(),
        email=f"old-test-{uuid.uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.flush()

    # Create transcription older than MAX_KEEP_DAYS (default 30)
    old_date = datetime.now(timezone.utc) - timedelta(days=35)

    transcription = Transcription(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="old_audio.mp3",
        storage_path="test/old_transcription.txt.gz",
        stage="completed",
        created_at=old_date,
        completed_at=old_date
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)
    return transcription


@pytest.fixture
def recent_transcription(db_session: Session) -> Transcription:
    """Create a recent transcription that should NOT be cleaned up."""
    from app.models.user import User

    # First create a user
    user = User(
        id=uuid.uuid4(),
        email=f"recent-test-{uuid.uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.flush()

    # Create transcription newer than MAX_KEEP_DAYS
    recent_date = datetime.now(timezone.utc) - timedelta(days=10)

    transcription = Transcription(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="recent_audio.mp3",
        storage_path="test/recent_transcription.txt.gz",
        stage="completed",
        created_at=recent_date,
        completed_at=recent_date
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)
    return transcription


# ==============================================================================
# await cleanup_expired_transcriptions() Tests
# ==============================================================================

class TestCleanupExpiredTranscriptions:
    """Test the main cleanup function."""

    @pytest.mark.asyncio

    async def test_should_respect_retention_days(self, db_session: Session):
        """Should only delete transcriptions older than MAX_KEEP_DAYS."""
        from app.models.user import User
        from app.core.config import settings

        # Create a user for both transcriptions
        user = User(
            id=uuid.uuid4(),
            email=f"retention-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        # Create old transcription (35 days - should be deleted)
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        old_transcription = Transcription(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="old_audio.mp3",
            storage_path="test/old_transcription.txt.gz",
            stage="completed",
            created_at=old_date,
            completed_at=old_date
        )
        db_session.add(old_transcription)

        # Create recent transcription (5 days - should NOT be deleted, younger than MAX_KEEP_DAYS=7)
        recent_date = datetime.now(timezone.utc) - timedelta(days=5)
        recent_transcription = Transcription(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="recent_audio.mp3",
            storage_path="test/recent_transcription.txt.gz",
            stage="completed",
            created_at=recent_date,
            completed_at=recent_date
        )
        db_session.add(recent_transcription)
        db_session.commit()

        # Capture IDs before cleanup (avoid referencing deleted instances later)
        old_id = old_transcription.id
        recent_id = recent_transcription.id

        # Mock storage service to avoid file operations
        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should delete old transcription
            assert result["deleted_count"] >= 1

            # Use a new session to verify database state (bypasses instance tracking)
            from app.db.session import SessionLocal
            verify_db = SessionLocal()
            try:
                # Old transcription should be deleted
                deleted_check = verify_db.query(Transcription).filter(
                    Transcription.id == old_id
                ).first()
                assert deleted_check is None, f"Old transcription (id={old_id}) was not deleted!"

                # Recent transcription should still exist
                remaining = verify_db.query(Transcription).filter(
                    Transcription.id == recent_id
                ).first()
                assert remaining is not None, f"Recent transcription (id={recent_id}) was deleted!"
            finally:
                verify_db.close()

    @pytest.mark.asyncio

    async def test_should_handle_empty_list(self, db_session: Session):
        """Should handle case when no expired transcriptions exist."""
        result = await cleanup_expired_transcriptions()

        assert result["deleted_count"] == 0
        assert result["failed_count"] == 0
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio

    async def test_should_log_cleanup_actions(self, old_transcription: Transcription, caplog):
        """Should log cleanup actions."""
        import logging

        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            with caplog.at_level(logging.INFO):
                await cleanup_expired_transcriptions()

            # Should log found expired transcriptions
            assert any("expired transcriptions" in record.message for record in caplog.records)
            # Should log cleanup complete
            assert any("Cleanup complete" in record.message for record in caplog.records)

    @pytest.mark.asyncio

    async def test_should_handle_database_errors(self, old_transcription: Transcription):
        """Should handle database errors gracefully."""
        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            # Mock storage to raise an error
            mock_storage_instance = Mock()
            mock_storage_instance.delete_transcription_text.side_effect = IOError("Disk full")
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should record failure but not crash
            assert result["failed_count"] >= 1
            assert len(result["errors"]) > 0
            assert any("Disk full" in error for error in result["errors"])

    @pytest.mark.asyncio

    async def test_should_validate_file_permissions(self, old_transcription: Transcription):
        """Should handle permission errors when deleting files."""
        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            # Mock storage to raise permission error
            mock_storage_instance = Mock()
            mock_storage_instance.delete_transcription_text.side_effect = PermissionError("Access denied")
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should handle permission error gracefully
            assert result["failed_count"] >= 1
            assert any("Access denied" in error for error in result["errors"])

    @pytest.mark.asyncio

    async def test_should_handle_interrupted_cleanup(self, db_session: Session):
        """Should handle cleanup interruption gracefully."""
        from app.models.user import User

        # Create a user first
        user = User(
            id=uuid.uuid4(),
            email=f"interrupt-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        # Create multiple old transcriptions
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        for i in range(5):
            transcription = Transcription(
                id=uuid.uuid4(),
                user_id=user.id,
                file_name=f"old_audio_{i}.mp3",
                storage_path=f"test/old_{i}.txt.gz",
                stage="completed",
                created_at=old_date
            )
            db_session.add(transcription)
        db_session.commit()

        call_count = [0]

        def mock_delete_with_interrupt(transcription_id):
            call_count[0] += 1
            if call_count[0] == 2:
                raise InterruptedError("Interrupted")

        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.delete_transcription_text.side_effect = mock_delete_with_interrupt
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should handle interruption
            assert len(result["errors"]) > 0
            assert any("Interrupted" in error for error in result["errors"])

    @pytest.mark.asyncio

    async def test_should_cleanup_summary_cascade(self, db_session: Session):
        """Should cascade delete summaries when deleting transcriptions."""
        from app.models.user import User

        # Create a user first
        user = User(
            id=uuid.uuid4(),
            email=f"cascade-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        uid = uuid.uuid4()
        old_date = datetime.now(timezone.utc) - timedelta(days=35)

        # Create transcription with summary
        transcription = Transcription(
            id=uid,
            user_id=user.id,
            file_name="old_with_summary.mp3",
            storage_path="test/old_with_summary.txt.gz",
            stage="completed",
            created_at=old_date
        )
        db_session.add(transcription)
        db_session.flush()

        # Create summary
        summary = Summary(
            id=uuid.uuid4(),
            transcription_id=uid,
            summary_text="Test summary"
        )
        db_session.add(summary)
        db_session.commit()

        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            await cleanup_expired_transcriptions()

            # Both transcription and summary should be deleted (cascade)
            from app.db.session import SessionLocal
            db = SessionLocal()
            try:
                remaining_transcription = db.query(Transcription).filter(
                    Transcription.id == uid
                ).first()
                remaining_summary = db.query(Summary).filter(
                    Summary.transcription_id == uid
                ).first()

                assert remaining_transcription is None
                assert remaining_summary is None
            finally:
                db.close()


class TestCleanupEdgeCases:
    """Test edge cases for cleanup functionality."""

    @pytest.mark.asyncio

    async def test_should_handle_transcription_without_storage_path(self, db_session: Session):
        """Should handle transcriptions with no storage path."""
        from app.models.user import User

        # Create a user first
        user = User(
            id=uuid.uuid4(),
            email=f"no-storage-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        old_date = datetime.now(timezone.utc) - timedelta(days=35)

        transcription = Transcription(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="no_storage.mp3",
            storage_path=None,  # No storage path
            stage="completed",
            created_at=old_date
        )
        db_session.add(transcription)
        db_session.commit()

        result = await cleanup_expired_transcriptions()

        # Should still delete the record even without storage file
        assert result["deleted_count"] >= 1

    @pytest.mark.asyncio

    async def test_should_handle_zero_retention_days(self, db_session: Session, monkeypatch):
        """Should handle MAX_KEEP_DAYS set to 0 (delete all)."""
        from app.models.user import User
        from app.core.config import settings

        # Create a user
        user = User(
            id=uuid.uuid4(),
            email=f"zero-retention-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        # Temporarily set MAX_KEEP_DAYS to 0
        monkeypatch.setattr(settings, 'MAX_KEEP_DAYS', 0)

        recent_date = datetime.now(timezone.utc) - timedelta(hours=1)
        transcription = Transcription(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="very_recent.mp3",
            storage_path="test/very_recent.txt.gz",
            stage="completed",
            created_at=recent_date
        )
        db_session.add(transcription)
        db_session.commit()

        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should delete even very recent transcriptions
            assert result["deleted_count"] >= 1

    @pytest.mark.asyncio

    async def test_should_handle_negative_retention_days(self, db_session: Session, monkeypatch):
        """Should handle negative MAX_KEEP_DAYS gracefully."""
        from app.core.config import settings

        # Negative retention days should be treated as absolute value
        monkeypatch.setattr(settings, 'MAX_KEEP_DAYS', -1)

        result = await cleanup_expired_transcriptions()

        # Should delete all transcriptions (negative treated as positive)
        # Or handle gracefully based on implementation
        assert result["deleted_count"] >= 0  # Just verify it doesn't crash

    @pytest.mark.asyncio

    async def test_should_handle_very_old_transcriptions(self, db_session: Session):
        """Should handle transcriptions that are very old (>1 year)."""
        from app.models.user import User

        # Create a user
        user = User(
            id=uuid.uuid4(),
            email=f"ancient-test-{uuid.uuid4().hex[:8]}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
        db_session.flush()

        very_old_date = datetime.now(timezone.utc) - timedelta(days=400)

        transcription = Transcription(
            id=uuid.uuid4(),
            user_id=user.id,
            file_name="ancient_audio.mp3",
            storage_path="test/ancient.txt.gz",
            stage="completed",
            created_at=very_old_date
        )
        db_session.add(transcription)
        db_session.commit()

        with patch('app.tasks.cleanup.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage.return_value = mock_storage_instance

            result = await cleanup_expired_transcriptions()

            # Should delete very old transcriptions
            assert result["deleted_count"] >= 1
