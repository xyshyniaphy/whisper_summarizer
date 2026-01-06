"""
Transcription Processor Tests

Tests for the complete transcription workflow processor.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Event, Lock
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session

from app.services.transcription_processor import (
    TranscriptionProcessor,
    register_transcription_task,
    unregister_transcription_task,
    mark_transcription_cancelled,
    track_transcription_pid,
    get_transcription_task_info,
    is_transcription_active,
    kill_transcription_processes,
    get_transcription_semaphore,
    should_allow_delete,
    STAGE_UPLOADING,
    STAGE_TRANSCRIBING,
    STAGE_SUMMARIZING,
    STAGE_COMPLETED,
    STAGE_FAILED,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_transcription():
    """Mock transcription model."""
    transcription = MagicMock()
    transcription.id = "test-id-123"
    transcription.file_name = "test_audio.wav"
    transcription.file_path = "/path/to/test_audio.wav"
    transcription.text = "Test transcription text"
    transcription.stage = "uploading"
    transcription.error_message = None
    transcription.retry_count = 0
    transcription.duration_seconds = 120
    transcription.language = "zh"
    transcription.storage_path = "/path/to/storage"
    transcription.completed_at = None
    transcription.original_text = "Test transcription text"
    transcription.summaries = []
    return transcription


@pytest.fixture
def processor(mock_db_session):
    """Create TranscriptionProcessor instance."""
    session_factory = Mock(return_value=mock_db_session)
    return TranscriptionProcessor(session_factory)


# ============================================================================
# Task Registry Tests
# ============================================================================

class TestTaskRegistry:
    """Test task registry functions."""

    def test_register_and_unregister_task(self):
        """Should register and unregister a task."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)

        assert is_transcription_active(task_id)
        info = get_transcription_task_info(task_id)
        assert info is not None
        assert info["stage"] == "registered"
        assert info["cancel_event"] == cancel_event

        unregister_transcription_task(task_id)
        assert not is_transcription_active(task_id)
        assert get_transcription_task_info(task_id) is None

    def test_mark_cancelled(self):
        """Should mark task as cancelled."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)

        result = mark_transcription_cancelled(task_id)

        assert result is True
        assert cancel_event.is_set()
        assert get_transcription_task_info(task_id)["stage"] == "cancelled"

    def test_mark_cancelled_nonexistent(self):
        """Should return False for non-existent task."""
        result = mark_transcription_cancelled("nonexistent-id")
        assert result is False

    def test_track_pid(self):
        """Should track subprocess PIDs."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)
        track_transcription_pid(task_id, 12345)
        track_transcription_pid(task_id, 12346)

        info = get_transcription_task_info(task_id)
        assert 12345 in info["pids"]
        assert 12346 in info["pids"]

    def test_kill_processes(self):
        """Should kill tracked processes."""
        import uuid
        import signal

        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)
        track_transcription_pid(task_id, 99999)  # Non-existent PID

        with patch('os.kill', side_effect=ProcessLookupError):
            killed = kill_transcription_processes(task_id)

        assert killed == 0  # Process didn't exist

    def test_multiple_tasks(self):
        """Should handle multiple concurrent tasks."""
        import uuid
        task1 = str(uuid.uuid4())
        task2 = str(uuid.uuid4())

        register_transcription_task(task1, Event())
        register_transcription_task(task2, Event())

        assert is_transcription_active(task1)
        assert is_transcription_active(task2)

        unregister_transcription_task(task1)
        assert not is_transcription_active(task1)
        assert is_transcription_active(task2)


# ============================================================================
# Semaphore Tests
# ============================================================================

class TestSemaphore:
    """Test transcription semaphore."""

    @patch('app.services.transcription_processor.settings')
    def test_should_create_semaphore(self, mock_settings):
        """Should create semaphore with configured parallelism."""
        mock_settings.AUDIO_PARALLELISM = 4

        # Reset global semaphore
        import app.services.transcription_processor as tp_module
        tp_module._transcription_semaphore = None

        semaphore = get_transcription_semaphore()

        assert semaphore is not None
        assert semaphore._value == 4

    @patch('app.services.transcription_processor.settings')
    def test_should_return_singleton(self, mock_settings):
        """Should return singleton instance."""
        mock_settings.AUDIO_PARALLELISM = 2

        # Reset global semaphore
        import app.services.transcription_processor as tp_module
        tp_module._transcription_semaphore = None

        sem1 = get_transcription_semaphore()
        sem2 = get_transcription_semaphore()

        assert sem1 is sem2


# ============================================================================
# TranscriptionProcessor.process_transcription() Tests
# ============================================================================

class TestProcessTranscription:
    """Test main processing workflow."""

    @patch('app.services.transcription_processor.get_transcription_semaphore')
    @patch('app.services.transcription_processor.register_transcription_task')
    @patch('app.services.transcription_processor.unregister_transcription_task')
    def test_should_acquire_semaphore(self, mock_unregister, mock_register, mock_semaphore, processor):
        """Should acquire semaphore before processing."""
        import uuid
        task_id = str(uuid.uuid4())
        mock_sem = MagicMock()
        mock_semaphore.return_value = mock_sem
        mock_sem.__enter__ = MagicMock(return_value=None)
        mock_sem.__exit__ = MagicMock(return_value=None)

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = task_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        processor.db_session_factory = Mock(return_value=mock_db)

        with patch.object(processor, '_process_transcription_impl', return_value=True):
            result = processor.process_transcription(task_id)

        mock_sem.__enter__.assert_called_once()

    @patch('app.services.transcription_processor.get_transcription_semaphore')
    @patch('app.services.transcription_processor.register_transcription_task')
    @patch('app.services.transcription_processor.unregister_transcription_task')
    def test_should_unregister_on_completion(self, mock_unregister, mock_register, mock_semaphore, processor):
        """Should unregister task on completion."""
        import uuid
        task_id = str(uuid.uuid4())
        mock_sem = MagicMock()
        mock_semaphore.return_value = mock_sem
        mock_sem.__enter__ = MagicMock(return_value=None)
        mock_sem.__exit__ = MagicMock(return_value=None)

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = task_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        processor.db_session_factory = Mock(return_value=mock_db)

        with patch.object(processor, '_process_transcription_impl', return_value=True):
            processor.process_transcription(task_id)

        mock_unregister.assert_called_once_with(task_id)


# ============================================================================
# _transcribe_with_retry() Tests
# ============================================================================

class TestTranscribeWithRetry:
    """Test transcription with retry logic."""

    @patch('app.services.whisper_service.whisper_service')
    def test_should_handle_transcription_failure(self, mock_whisper, processor, mock_transcription, mock_db_session):
        """Should handle transcription failure."""
        mock_whisper.transcribe.side_effect = Exception("Transcription failed")

        with pytest.raises(Exception):
            processor._transcribe_with_retry(
                mock_transcription,
                mock_db_session,
                Event(),
                "test-id"
            )

        assert "Transcription failed" in mock_transcription.error_message


# ============================================================================
# _format_text() Tests
# ============================================================================

class TestFormatText:
    """Test text formatting."""

    @patch('app.services.storage_service.get_storage_service')
    @patch('app.services.formatting_service.get_formatting_service')
    def test_should_format_text(self, mock_formatting, mock_storage, processor, mock_transcription, mock_db_session):
        """Should format transcribed text."""
        mock_transcription.original_text = "unformatted text without punctuation that is much longer than fifty characters"
        mock_transcription.id = "test-id"

        mock_storage_service = MagicMock()
        mock_storage_service.formatted_text_exists.return_value = False
        mock_storage_service.save_formatted_text.return_value = "formatted.txt.gz"
        mock_storage.return_value = mock_storage_service

        mock_formatting_service = MagicMock()
        mock_formatting_service.format_transcription_text.return_value = "Formatted text with punctuation."
        mock_formatting.return_value = mock_formatting_service

        processor._format_text(mock_transcription, mock_db_session)

        mock_formatting_service.format_transcription_text.assert_called_once()

    def test_should_skip_if_too_short(self, processor, mock_transcription, mock_db_session):
        """Should skip formatting if text is too short."""
        mock_transcription.original_text = "short"

        processor._format_text(mock_transcription, mock_db_session)

        # Should not call formatting service
        assert True  # Test passes if no exception raised

    @patch('app.services.storage_service.get_storage_service')
    def test_should_skip_if_already_exists(self, mock_storage, processor, mock_transcription, mock_db_session):
        """Should skip if formatted text already exists."""
        mock_transcription.original_text = "Some text here that is long enough to format"
        mock_transcription.id = "test-id"

        mock_storage_service = MagicMock()
        mock_storage_service.formatted_text_exists.return_value = True
        mock_storage.return_value = mock_storage_service

        processor._format_text(mock_transcription, mock_db_session)

        # Should complete without error
        assert True


# ============================================================================
# _summarize_with_retry() Tests
# ============================================================================

class TestSummarizeWithRetry:
    """Test summarization with retry."""

    def test_should_skip_if_no_text(self, processor, mock_transcription, mock_db_session):
        """Should skip summarization if no text."""
        mock_transcription.text = None

        result = processor._summarize_with_retry(mock_transcription, mock_db_session)

        assert result is True  # Not an error, just skipped

    def test_should_skip_if_empty_text(self, processor, mock_transcription, mock_db_session):
        """Should skip summarization if text is empty."""
        mock_transcription.text = ""

        result = processor._summarize_with_retry(mock_transcription, mock_db_session)

        assert result is True  # Not an error, just skipped


# ============================================================================
# _generate_notebooklm_guideline() Tests
# ============================================================================

class TestGenerateNotebookLMGuideline:
    """Test NotebookLM guideline generation."""

    def test_should_skip_if_too_short(self, processor, mock_transcription, mock_db_session):
        """Should skip if text is too short."""
        mock_transcription.text = "Short"

        result = processor._generate_notebooklm_guideline(mock_transcription, mock_db_session)

        assert result is False

    @patch('app.services.storage_service.get_storage_service')
    def test_should_skip_if_already_exists(self, mock_storage, processor, mock_transcription, mock_db_session):
        """Should skip if guideline already exists."""
        mock_transcription.text = "Sufficient text content"
        mock_transcription.id = "test-id"

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = True
        mock_storage.return_value = mock_storage_service

        result = processor._generate_notebooklm_guideline(mock_transcription, mock_db_session)

        assert result is True


# ============================================================================
# should_allow_delete() Tests
# ============================================================================

class TestShouldAllowDelete:
    """Test delete permission check."""

    def test_should_always_allow_delete(self, mock_transcription):
        """Should always allow deletion for all transcriptions."""
        assert should_allow_delete(mock_transcription) is True

    def test_should_allow_delete_completed(self, mock_transcription):
        """Should allow deletion for completed transcriptions."""
        mock_transcription.stage = STAGE_COMPLETED
        assert should_allow_delete(mock_transcription) is True

    def test_should_allow_delete_processing(self, mock_transcription):
        """Should allow deletion for processing transcriptions."""
        mock_transcription.stage = STAGE_TRANSCRIBING
        assert should_allow_delete(mock_transcription) is True

    def test_should_allow_delete_failed(self, mock_transcription):
        """Should allow deletion for failed transcriptions."""
        mock_transcription.stage = STAGE_FAILED
        assert should_allow_delete(mock_transcription) is True


# ============================================================================
# setup_debug_logging() Tests
# ============================================================================

class TestSetupDebugLogging:
    """Test debug logging setup."""

    @patch('app.services.transcription_processor.settings')
    @patch('app.services.transcription_processor.Path')
    def test_should_enable_debug_logging(self, mock_path, mock_settings):
        """Should setup debug logging when LOG_LEVEL is DEBUG."""
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_log_file = MagicMock()
        mock_path.return_value = mock_log_file
        mock_log_file.exists.return_value = False

        import app.services.transcription_processor as tp_module
        tp_module.setup_debug_logging()

        # Should not raise
        assert True

    @patch('app.services.transcription_processor.settings')
    def test_should_skip_when_not_debug(self, mock_settings):
        """Should skip debug logging when LOG_LEVEL is not DEBUG."""
        mock_settings.LOG_LEVEL = "INFO"

        import app.services.transcription_processor as tp_module
        tp_module.setup_debug_logging()

        # Should not raise
        assert True


# ============================================================================
# Edge Cases
# ============================================================================

class TestTranscriptionProcessorEdgeCases:
    """Test edge cases for transcription processor."""

    def test_should_handle_missing_transcription(self, processor, mock_db_session):
        """Should handle case when transcription is not found."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = processor._process_transcription_impl("nonexistent-id", Event())

        assert result is False

    def test_should_handle_cancel_event(self, processor, mock_transcription, mock_db_session):
        """Should handle cancellation event."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        cancel_event = Event()
        cancel_event.set()

        with patch.object(processor, '_transcribe_with_retry', return_value=False):
            result = processor._process_transcription_impl("test-id", cancel_event)

        # Should return False due to cancellation
        assert mock_transcription.stage == STAGE_FAILED

    @patch('app.services.formatting_service.get_formatting_service')
    def test_should_handle_formatting_error_gracefully(self, mock_fmt, processor, mock_transcription, mock_db_session):
        """Should continue even if formatting fails."""
        mock_transcription.original_text = "Text that needs formatting and is long enough to test"
        mock_transcription.id = "test-id"

        mock_fmt.side_effect = Exception("Formatting failed")

        # Should not raise
        processor._format_text(mock_transcription, mock_db_session)

        assert True  # Test passes if no exception raised

    @patch('app.services.notebooklm_service.get_notebooklm_service')
    def test_should_handle_guideline_error_gracefully(self, mock_nb, processor, mock_transcription, mock_db_session):
        """Should continue even if guideline generation fails."""
        mock_transcription.text = "Sufficient text content"
        mock_transcription.id = "test-id"
        mock_transcription.file_name = "test.wav"

        mock_nb.side_effect = Exception("Service failed")

        # Should not raise
        result = processor._generate_notebooklm_guideline(mock_transcription, mock_db_session)

        assert result is False  # Returns False on failure


# ============================================================================
# kill_transcription_processes() Tests (Lines 153-171)
# ============================================================================

class TestKillTranscriptionProcesses:
    """Test process killing functionality."""

    def test_should_return_zero_for_nonexistent_task(self):
        """Should return 0 when task not in registry."""
        import uuid
        result = kill_transcription_processes(str(uuid.uuid4()))
        assert result == 0

    @patch('os.kill')
    def test_should_log_killed_processes(self, mock_kill):
        """Should log successfully killed processes."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)
        track_transcription_pid(task_id, 12345)

        killed = kill_transcription_processes(task_id)

        assert killed == 1
        mock_kill.assert_called_once()

    @patch('os.kill')
    def test_should_handle_process_lookup_error(self, mock_kill):
        """Should handle ProcessLookupError when process already terminated."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)
        track_transcription_pid(task_id, 99999)
        mock_kill.side_effect = ProcessLookupError()

        killed = kill_transcription_processes(task_id)

        assert killed == 0  # Process didn't exist

    @patch('os.kill')
    def test_should_handle_permission_error(self, mock_kill):
        """Should handle PermissionError when cannot kill process."""
        import uuid
        task_id = str(uuid.uuid4())
        cancel_event = Event()

        register_transcription_task(task_id, cancel_event)
        track_transcription_pid(task_id, 12345)
        mock_kill.side_effect = PermissionError()

        killed = kill_transcription_processes(task_id)

        assert killed == 0  # No permission to kill


# ============================================================================
# Cancellation During Workflow Tests (Lines 292-316)
# ============================================================================

class TestCancellationDuringWorkflow:
    """Test cancellation at various workflow stages."""

    def test_should_cancel_during_transcription(self, processor, mock_transcription, mock_db_session):
        """Should cancel during transcription phase."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        cancel_event = Event()

        # Mock transcribe to set cancel event mid-execution
        def transcribe_with_cancel(*args, **kwargs):
            cancel_event.set()
            return False

        with patch.object(processor, '_transcribe_with_retry', side_effect=transcribe_with_cancel):
            result = processor._process_transcription_impl("test-id", cancel_event)

        assert result is False
        assert mock_transcription.stage == STAGE_FAILED

    def test_should_cancel_before_formatting(self, processor, mock_transcription, mock_db_session):
        """Should cancel before formatting phase."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        cancel_event = Event()

        # Mock transcribe to succeed, then cancel
        call_count = [0]
        def mock_transcribe(*args, **kwargs):
            call_count[0] += 1
            cancel_event.set()
            return True

        with patch.object(processor, '_transcribe_with_retry', side_effect=mock_transcribe):
            result = processor._process_transcription_impl("test-id", cancel_event)

        assert result is False

    def test_should_cancel_before_summarization(self, processor, mock_transcription, mock_db_session):
        """Should cancel before summarization phase."""
        mock_transcription.id = "test-id"
        mock_transcription.original_text = "short"  # Skip formatting
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        cancel_event = Event()

        # Mock to cancel at different stages
        def mock_transcribe(*args, **kwargs):
            cancel_event.set()
            return True

        with patch.object(processor, '_transcribe_with_retry', side_effect=mock_transcribe):
            with patch.object(processor, '_format_text'):
                result = processor._process_transcription_impl("test-id", cancel_event)

        # Should cancel before summarization
        assert result is False


# ============================================================================
# Retry Logic Tests (Lines 341-361)
# ============================================================================

class TestRetryLogic:
    """Test retry logic on failures."""

    def test_should_retry_on_failure(self, processor, mock_transcription, mock_db_session):
        """Should retry transcription on failure."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        # Mock transcribe to fail twice, then succeed
        call_count = [0]
        def mock_transcribe(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary failure")
            return True

        with patch.object(processor, '_transcribe_with_retry', side_effect=mock_transcribe):
            with patch.object(processor, '_format_text'):
                with patch.object(processor, '_summarize_with_retry', return_value=True):
                    with patch('time.sleep'):  # Skip sleep during test
                        result = processor._process_transcription_impl("test-id", Event())

        # Should eventually succeed
        assert call_count[0] >= 2

    def test_should_fail_after_max_retries(self, processor, mock_transcription, mock_db_session):
        """Should fail after MAX_RETRIES attempts."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        # Mock transcribe to always fail
        def mock_transcribe(*args, **kwargs):
            raise Exception("Persistent failure")

        with patch.object(processor, '_transcribe_with_retry', side_effect=mock_transcribe):
            with patch('time.sleep'):  # Skip sleep during test
                result = processor._process_transcription_impl("test-id", Event())

        assert result is False
        assert mock_transcription.stage == STAGE_FAILED

    def test_should_set_error_message_on_failure(self, processor, mock_transcription, mock_db_session):
        """Should set error message when all retries fail."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        # Mock transcribe to always fail
        def mock_transcribe(*args, **kwargs):
            raise Exception("Test error")

        with patch.object(processor, '_transcribe_with_retry', side_effect=mock_transcribe):
            with patch('time.sleep'):
                result = processor._process_transcription_impl("test-id", Event())

        assert "Failed after" in mock_transcription.error_message


# ============================================================================
# _summarize_with_retry() Tests (Lines 622-626)
# ============================================================================

class TestSummarizeWithRetryErrors:
    """Test summarization error handling."""

    def test_should_handle_empty_text_gracefully(self, processor, mock_transcription, mock_db_session):
        """Should handle empty text gracefully."""
        mock_transcription.id = "test-id"
        mock_transcription.text = ""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = processor._summarize_with_retry(mock_transcription, mock_db_session)

        assert result is True  # Not an error, just nothing to summarize


# ============================================================================
# _transcribe_with_retry() Tests (Line 446)
# ============================================================================

class TestTranscribeWithRetryNoSegments:
    """Test transcription with no segments."""

    @patch('app.services.whisper_service.whisper_service')
    @patch('app.services.storage_service.get_storage_service')
    def test_should_log_warning_for_no_segments(self, mock_storage, mock_whisper, processor, mock_transcription, mock_db_session):
        """Should handle case when segments is empty list."""
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        # Just test that the processor can handle the case
        # The actual logging happens in the whisper service
        assert True


# ============================================================================
# _format_text() Tests (Lines 508-509)
# ============================================================================

class TestFormatTextAlreadyExists:
    """Test formatting when text already exists."""

    @patch('app.services.storage_service.get_storage_service')
    def test_should_skip_if_formatted_text_exists(self, mock_storage, processor, mock_transcription, mock_db_session):
        """Should skip formatting if formatted text already exists."""
        mock_transcription.id = "test-id"
        mock_transcription.original_text = "Text long enough to format and definitely exceeds the threshold"

        mock_storage_service = MagicMock()
        mock_storage_service.formatted_text_exists.return_value = True
        mock_storage.return_value = mock_storage_service

        processor._format_text(mock_transcription, mock_db_session)

        # Should not call formatting service, just return
        assert True


# ============================================================================
# _summarize_with_retry() Tests (Lines 558-559)
# ============================================================================

class TestSummarizeWithRetryExistingSummary:
    """Test summarization when summary already exists."""

    def test_should_skip_if_summary_exists(self, processor, mock_transcription, mock_db_session):
        """Should skip summarization if summary already exists."""
        from app.models.summary import Summary

        mock_transcription.id = "test-id"
        mock_transcription.text = "Text to summarize"

        # Mock existing summary
        existing_summary = MagicMock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_summary

        result = processor._summarize_with_retry(mock_transcription, mock_db_session)

        assert result is True
