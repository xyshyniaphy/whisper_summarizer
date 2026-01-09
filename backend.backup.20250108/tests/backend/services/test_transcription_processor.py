"""
Tests for TranscriptionProcessor - Complete transcription workflow service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from threading import Event
from datetime import datetime
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
    STAGE_UPLOADING,
    STAGE_TRANSCRIBING,
    STAGE_SUMMARIZING,
    STAGE_COMPLETED,
    STAGE_FAILED,
    should_allow_delete
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock(spec=Session)

    # Mock query chain
    mock_query = Mock()
    session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None

    return session


@pytest.fixture
def mock_db_session_factory(mock_db_session):
    """Create a mock database session factory."""
    return lambda: mock_db_session


@pytest.fixture
def mock_transcription():
    """Create a mock transcription object."""
    transcription = Mock()
    transcription.id = "test-id-123"
    transcription.file_name = "test_audio.mp3"
    transcription.file_path = "/path/to/audio.mp3"
    transcription.storage_path = None
    transcription.language = None
    transcription.duration_seconds = None
    transcription.stage = "uploading"
    transcription.error_message = None
    transcription.retry_count = 0
    transcription.completed_at = None
    transcription.original_text = "Test transcription text"
    transcription.summaries = []
    transcription.text = "Test transcription text"
    return transcription


@pytest.fixture
def transcription_processor(mock_db_session_factory):
    """Create a TranscriptionProcessor instance."""
    return TranscriptionProcessor(mock_db_session_factory)


class TestTranscriptionProcessorInitialization:
    """Tests for TranscriptionProcessor initialization."""

    def test_init_sets_session_factory(self, mock_db_session_factory):
        """Test that session factory is stored."""
        processor = TranscriptionProcessor(mock_db_session_factory)
        assert processor.db_session_factory == mock_db_session_factory

    @patch('app.services.transcription_processor.setup_debug_logging')
    def test_calls_setup_debug_logging(self, mock_setup):
        """Test that setup_debug_logging is called on init."""
        TranscriptionProcessor(lambda: Mock())
        mock_setup.assert_called_once()


class TestGetTranscriptionSemaphore:
    """Tests for get_transcription_semaphore function."""

    @patch('app.services.transcription_processor._transcription_semaphore', None)
    @patch('app.services.transcription_processor.settings')
    def test_creates_new_semaphore(self, mock_settings):
        """Test that new semaphore is created when None exists."""
        mock_settings.AUDIO_PARALLELISM = 2

        semaphore = get_transcription_semaphore()

        assert semaphore is not None
        # Should be BoundedSemaphore with value 2
        assert semaphore._value == 2

    @patch('app.services.transcription_processor._transcription_semaphore', None)
    @patch('app.services.transcription_processor.settings')
    def test_returns_singleton(self, mock_settings):
        """Test that same semaphore instance is returned."""
        mock_settings.AUDIO_PARALLELISM = 2

        semaphore1 = get_transcription_semaphore()
        semaphore2 = get_transcription_semaphore()

        assert semaphore1 is semaphore2


class TestTaskRegistry:
    """Tests for task registry functions."""

    def test_register_task(self):
        """Test registering a new transcription task."""
        cancel_event = Event()

        register_transcription_task("test-id", cancel_event)

        assert is_transcription_active("test-id")
        task_info = get_transcription_task_info("test-id")
        assert task_info is not None
        assert task_info["cancel_event"] is cancel_event
        assert task_info["stage"] == "registered"

    def test_unregister_task(self):
        """Test unregistering a task."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)

        unregister_transcription_task("test-id")

        assert not is_transcription_active("test-id")
        assert get_transcription_task_info("test-id") is None

    def test_mark_cancelled(self):
        """Test marking a task as cancelled."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)

        result = mark_transcription_cancelled("test-id")

        assert result is True
        assert cancel_event.is_set()

        task_info = get_transcription_task_info("test-id")
        assert task_info["stage"] == "cancelled"

    def test_mark_cancelled_nonexistent_task(self):
        """Test cancelling non-existent task returns False."""
        result = mark_transcription_cancelled("nonexistent")
        assert result is False

    def test_track_pid(self):
        """Test tracking a subprocess PID."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)

        track_transcription_pid("test-id", 12345)

        task_info = get_transcription_task_info("test-id")
        assert 12345 in task_info["pids"]

    def test_is_active(self):
        """Test checking if task is active."""
        # Use a unique ID that won't conflict with other tests
        test_id = "test-is-active-unique-id"
        cancel_event = Event()

        # First ensure the test_id is not already registered (cleanup from previous tests)
        if is_transcription_active(test_id):
            unregister_transcription_task(test_id)

        assert not is_transcription_active(test_id)

        register_transcription_task(test_id, cancel_event)
        assert is_transcription_active(test_id)

        # Cleanup
        unregister_transcription_task(test_id)


class TestKillTranscriptionProcesses:
    """Tests for kill_transcription_processes function."""

    def test_kill_processes(self):
        """Test killing tracked processes."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)
        track_transcription_pid("test-id", 12345)
        track_transcription_pid("test-id", 67890)

        with patch('os.kill') as mock_kill:
            killed = kill_transcription_processes("test-id")

            assert killed == 2
            assert mock_kill.call_count == 2

    def test_kill_nonexistent_task(self):
        """Test killing processes for non-existent task."""
        killed = kill_transcription_processes("nonexistent")
        assert killed == 0

    def test_kill_process_already_terminated(self):
        """Test handling of already terminated process."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)
        track_transcription_pid("test-id", 12345)

        import signal
        import os

        with patch('os.kill', side_effect=ProcessLookupError()):
            killed = kill_transcription_processes("test-id")

            # Should handle gracefully
            assert killed == 0

    def test_kill_process_no_permission(self):
        """Test handling of permission error."""
        cancel_event = Event()
        register_transcription_task("test-id", cancel_event)
        track_transcription_pid("test-id", 12345)

        with patch('os.kill', side_effect=PermissionError()):
            killed = kill_transcription_processes("test-id")

            # Should handle gracefully
            assert killed == 0


class TestProcessTranscription:
    """Tests for process_transcription method."""

    def test_successful_workflow(self, transcription_processor, mock_db_session, mock_transcription):
        """Test complete successful workflow."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch.object(transcription_processor, '_process_transcription_impl', return_value=True):
            result = transcription_processor.process_transcription("test-id")

            assert result is True

    def test_transcription_not_found(self, transcription_processor, mock_db_session):
        """Test handling of non-existent transcription."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = transcription_processor.process_transcription("nonexistent")

        assert result is False

    def test_cancellation_before_start(self, transcription_processor, mock_db_session):
        """Test cancellation before processing starts."""
        mock_transcription = Mock()
        mock_transcription.id = "test-id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch.object(transcription_processor, '_process_transcription_impl') as mock_impl:
            def cancel_before_start(*args, **kwargs):
                # Mark as cancelled when implementation is called
                mark_transcription_cancelled("test-id")
                return False

            mock_impl.side_effect = cancel_before_start

            result = transcription_processor.process_transcription("test-id")

            assert result is False


class TestTranscribeWithRetry:
    """Tests for _transcribe_with_retry method."""

    def test_successful_transcription(self, transcription_processor, mock_db_session, mock_transcription):
        """Test successful transcription."""
        with patch('app.services.transcription_processor.whisper_service') as mock_whisper:
            mock_whisper.transcribe.return_value = {
                "text": "Transcribed text",
                "segments": [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "Test"}],
                "language": "en",
                "duration": 120.0
            }

            with patch('app.services.storage_service.get_storage_service') as mock_storage:
                mock_storage_service = Mock()
                mock_storage_service.save_transcription_text.return_value = "test.txt.gz"
                mock_storage_service.save_transcription_segments.return_value = "segments.json.gz"
                mock_storage_service.save_original_output.return_value = "original.json.gz"
                mock_storage.return_value = mock_storage_service

                result = transcription_processor._transcribe_with_retry(
                    mock_transcription,
                    mock_db_session,
                    Event(),
                    "test-id"
                )

                assert result is True
                assert mock_transcription.stage == STAGE_TRANSCRIBING
                assert mock_transcription.language == "en"

    def test_transcription_cancelled(self, transcription_processor, mock_db_session, mock_transcription):
        """Test cancellation during transcription."""
        cancel_event = Event()
        cancel_event.set()

        with patch('app.services.transcription_processor.whisper_service') as mock_whisper:
            mock_whisper.transcribe.side_effect = Exception("Cancelled")

            # The implementation raises the exception, so we expect it to be raised
            with pytest.raises(Exception, match="Cancelled"):
                transcription_processor._transcribe_with_retry(
                    mock_transcription,
                    mock_db_session,
                    cancel_event,
                    "test-id"
                )

    def test_transcription_error_handling(self, transcription_processor, mock_db_session, mock_transcription):
        """Test handling of transcription errors."""
        with patch('app.services.transcription_processor.whisper_service') as mock_whisper:
            mock_whisper.transcribe.side_effect = Exception("Transcription failed")

            with pytest.raises(Exception, match="Transcription failed"):
                transcription_processor._transcribe_with_retry(
                    mock_transcription,
                    mock_db_session,
                    Event(),
                    "test-id"
                )


class TestFormatText:
    """Tests for _format_text method."""

    def test_successful_formatting(self, transcription_processor, mock_db_session, mock_transcription):
        """Test successful text formatting."""
        mock_transcription.original_text = "Test text without punctuation"

        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.formatted_text_exists.return_value = False
            mock_storage.save_formatted_text.return_value = "formatted.txt.gz"
            mock_storage_getter.return_value = mock_storage

            with patch('app.services.formatting_service.get_formatting_service') as mock_formatting_getter:
                mock_formatting = Mock()
                mock_formatting.format_transcription_text.return_value = "Test text, without punctuation."
                mock_formatting_getter.return_value = mock_formatting

                # Should not raise any exception
                transcription_processor._format_text(mock_transcription, mock_db_session)

    def test_skips_short_text(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that text shorter than 50 chars is skipped."""
        mock_transcription.original_text = "Short"

        # Should not raise any exception
        transcription_processor._format_text(mock_transcription, mock_db_session)

    def test_skips_existing_formatted_text(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that existing formatted text is not regenerated."""
        mock_transcription.original_text = "Test text that is long enough to format"

        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.formatted_text_exists.return_value = True
            mock_storage_getter.return_value = mock_storage

            # Should not raise any exception
            transcription_processor._format_text(mock_transcription, mock_db_session)

    def test_formatting_failure_doesnt_fail_workflow(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that formatting failure doesn't fail entire workflow."""
        mock_transcription.original_text = "Test text that should be formatted"

        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.formatted_text_exists.return_value = False
            mock_storage_getter.return_value = mock_storage

            with patch('app.services.formatting_service.get_formatting_service') as mock_formatting_getter:
                mock_formatting = Mock()
                mock_formatting.format_transcription_text.side_effect = Exception("API failed")
                mock_formatting_getter.return_value = mock_formatting

                # Should not raise any exception
                transcription_processor._format_text(mock_transcription, mock_db_session)


class TestSummarizeWithRetry:
    """Tests for _summarize_with_retry method."""

    def test_successful_summarization(self, transcription_processor, mock_db_session, mock_transcription):
        """Test successful summarization."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No existing summary

        mock_response = Mock()
        mock_response.status = "success"
        mock_response.summary = "AI generated summary"
        mock_response.model_name = "glm-4.5-air"
        mock_response.prompt = "Test prompt"
        mock_response.input_text_length = 1000
        mock_response.output_text_length = 100
        mock_response.input_tokens = 500
        mock_response.output_tokens = 50
        mock_response.total_tokens = 550
        mock_response.response_time_ms = 1500
        mock_response.temperature = 0.7

        # Create an async function that returns the mock response
        async def mock_generate_summary(*args, **kwargs):
            return mock_response

        with patch('app.services.transcription_processor.get_glm_client') as mock_glm_getter:
            mock_glm = Mock()
            mock_glm.generate_summary = mock_generate_summary
            mock_glm_getter.return_value = mock_glm

            result = transcription_processor._summarize_with_retry(
                mock_transcription,
                mock_db_session
            )

            assert result is True
            assert mock_transcription.stage == STAGE_SUMMARIZING

    def test_skips_existing_summary(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that existing summary is not regenerated."""
        mock_summary = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_summary

        result = transcription_processor._summarize_with_retry(
            mock_transcription,
            mock_db_session
        )

        assert result is True

    def test_handles_empty_text(self, transcription_processor, mock_db_session, mock_transcription):
        """Test handling of empty transcription text."""
        mock_transcription.text = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = transcription_processor._summarize_with_retry(
            mock_transcription,
            mock_db_session
        )

        assert result is True

    def test_summarization_error_handling(self, transcription_processor, mock_db_session, mock_transcription):
        """Test handling of summarization errors."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        mock_response = Mock()
        mock_response.status = "error"
        mock_response.error_message = "API error"

        # Create an async function that returns the error response
        async def mock_generate_summary_error(*args, **kwargs):
            return mock_response

        with patch('app.services.transcription_processor.get_glm_client') as mock_glm_getter:
            mock_glm = Mock()
            mock_glm.generate_summary = mock_generate_summary_error
            mock_glm_getter.return_value = mock_glm

            with pytest.raises(Exception, match="API error"):
                transcription_processor._summarize_with_retry(
                    mock_transcription,
                    mock_db_session
                )


class TestGenerateNotebookLMGuideline:
    """Tests for _generate_notebooklm_guideline method."""

    def test_successful_guideline_generation(self, transcription_processor, mock_db_session, mock_transcription):
        """Test successful NotebookLM guideline generation."""
        mock_transcription.text = "Text long enough for guideline generation " * 10

        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = False
            mock_storage.save_notebooklm_guideline.return_value = "guideline.txt"
            mock_storage_getter.return_value = mock_storage

            with patch('app.services.notebooklm_service.get_notebooklm_service') as mock_notebooklm_getter:
                mock_notebooklm = Mock()
                mock_notebooklm.generate_guideline.return_value = "## Presentation Guideline\n\n- Slide 1\n- Slide 2"
                mock_notebooklm_getter.return_value = mock_notebooklm

                result = transcription_processor._generate_notebooklm_guideline(
                    mock_transcription,
                    mock_db_session
                )

                assert result is True

    def test_skips_existing_guideline(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that existing guideline is not regenerated."""
        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage_getter.return_value = mock_storage

            result = transcription_processor._generate_notebooklm_guideline(
                mock_transcription,
                mock_db_session
            )

            assert result is True

    def test_skips_short_text(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that short text is skipped."""
        mock_transcription.text = "Short text"

        result = transcription_processor._generate_notebooklm_guideline(
            mock_transcription,
            mock_db_session
        )

        assert result is False

    def test_guideline_failure_is_non_critical(self, transcription_processor, mock_db_session, mock_transcription):
        """Test that guideline failure doesn't fail entire workflow."""
        mock_transcription.text = "Text long enough for guideline generation " * 10

        with patch('app.services.storage_service.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = False
            mock_storage_getter.return_value = mock_storage

            with patch('app.services.notebooklm_service.get_notebooklm_service') as mock_notebooklm_getter:
                mock_notebooklm = Mock()
                mock_notebooklm.generate_guideline.side_effect = Exception("API failed")
                mock_notebooklm_getter.return_value = mock_notebooklm

                # Should not raise any exception
                result = transcription_processor._generate_notebooklm_guideline(
                    mock_transcription,
                    mock_db_session
                )

                assert result is False


class TestShouldAllowDelete:
    """Tests for should_allow_delete function."""

    def test_allows_delete_for_completed_transcription(self):
        """Test that completed transcriptions can be deleted."""
        transcription = Mock()
        transcription.stage = STAGE_COMPLETED

        result = should_allow_delete(transcription)

        assert result is True

    def test_allows_delete_for_failed_transcription(self):
        """Test that failed transcriptions can be deleted."""
        transcription = Mock()
        transcription.stage = STAGE_FAILED

        result = should_allow_delete(transcription)

        assert result is True

    def test_allows_delete_for_processing_transcription(self):
        """Test that processing transcriptions can be deleted (will be cancelled)."""
        transcription = Mock()
        transcription.stage = STAGE_TRANSCRIBING

        result = should_allow_delete(transcription)

        assert result is True

    def test_allows_delete_for_any_transcription(self):
        """Test that all transcriptions are deletable."""
        transcription = Mock()
        transcription.stage = "any_stage"

        result = should_allow_delete(transcription)

        assert result is True


class TestProcessStageConstants:
    """Tests for stage constant definitions."""

    def test_stage_constants_defined(self):
        """Test that all stage constants are defined."""
        assert STAGE_UPLOADING == "uploading"
        assert STAGE_TRANSCRIBING == "transcribing"
        assert STAGE_SUMMARIZING == "summarizing"
        assert STAGE_COMPLETED == "completed"
        assert STAGE_FAILED == "failed"
