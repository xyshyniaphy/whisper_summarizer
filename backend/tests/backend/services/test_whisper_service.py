"""
Tests for WhisperService - faster-whisper audio transcription service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from threading import Event
from pathlib import Path

from app.services.whisper_service import TranscribeService, whisper_service


@pytest.fixture
def mock_whisper_model():
    """Create a mock WhisperModel."""
    mock_model = Mock()

    # Mock transcribe method
    mock_segments = [
        Mock(text="Hello world", start=0.0, end=2.5),
        Mock(text="This is a test", start=2.5, end=5.0),
        Mock(text="Final segment", start=5.0, end=7.5),
    ]

    mock_info = Mock()
    mock_info.language = "en"
    mock_info.language_probability = 0.95
    mock_info.duration = 7.5

    mock_model.transcribe.return_value = (mock_segments, mock_info)

    return mock_model


@pytest.fixture
def whisper_service_instance(mock_whisper_model):
    """Create a TranscribeService with mocked WhisperModel."""
    with patch('app.services.whisper_service.WhisperModel', return_value=mock_whisper_model):
        service = TranscribeService()
        service.model = mock_whisper_model
        return service


class TestTranscribeServiceInitialization:
    """Tests for TranscribeService initialization."""

    @patch.dict('os.environ', {
        'FASTER_WHISPER_DEVICE': 'cpu',
        'FASTER_WHISPER_COMPUTE_TYPE': 'int8',
        'FASTER_WHISPER_MODEL_SIZE': 'base'
    })
    @patch('app.services.whisper_service.settings')
    @patch('app.services.whisper_service.WhisperModel')
    def test_init_with_cpu_device(self, mock_model_cls, mock_settings):
        """Test initialization with CPU device."""
        mock_settings.WHISPER_LANGUAGE = "zh"
        mock_settings.WHISPER_THREADS = 4

        service = TranscribeService()

        assert service.device == "cpu"
        assert service.compute_type == "int8"
        assert service.model_size == "base"
        mock_model_cls.assert_called_once()

    @patch.dict('os.environ', {
        'FASTER_WHISPER_DEVICE': 'cuda',
        'FASTER_WHISPER_COMPUTE_TYPE': 'float16'
    })
    @patch('app.services.whisper_service.settings')
    @patch('app.services.whisper_service.WhisperModel')
    def test_init_with_cuda_device(self, mock_model_cls, mock_settings):
        """Test initialization with CUDA device."""
        mock_settings.WHISPER_LANGUAGE = "en"
        mock_settings.WHISPER_THREADS = 2

        service = TranscribeService()

        assert service.device == "cuda"
        assert service.compute_type == "float16"

    @patch('app.services.whisper_service.settings')
    @patch('app.services.whisper_service.WhisperModel')
    def test_model_initialization(self, mock_model_cls, mock_settings):
        """Test that WhisperModel is initialized correctly."""
        mock_settings.WHISPER_LANGUAGE = "zh"
        mock_settings.WHISPER_THREADS = 4

        service = TranscribeService()

        mock_model_cls.assert_called_once()
        call_kwargs = mock_model_cls.call_args[1]
        assert call_kwargs['device'] == service.device
        assert call_kwargs['compute_type'] == service.compute_type
        assert call_kwargs['num_workers'] == 4


class TestGetAudioDuration:
    """Tests for _get_audio_duration method."""

    def test_get_duration_success(self, whisper_service_instance):
        """Test successful audio duration retrieval."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "123.45"

            duration = whisper_service_instance._get_audio_duration("/path/to/audio.mp3")

            assert duration == 123
            mock_run.assert_called_once()

    def test_get_duration_timeout(self, whisper_service_instance):
        """Test handling of ffprobe timeout."""
        import subprocess

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 30)

            duration = whisper_service_instance._get_audio_duration("/path/to/audio.mp3")

            assert duration == 0

    def test_get_duration_process_error(self, whisper_service_instance):
        """Test handling of ffprobe process error."""
        import subprocess

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")

            duration = whisper_service_instance._get_audio_duration("/path/to/audio.mp3")

            assert duration == 0

    def test_get_duration_invalid_output(self, whisper_service_instance):
        """Test handling of invalid ffprobe output."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "invalid"

            duration = whisper_service_instance._get_audio_duration("/path/to/audio.mp3")

            assert duration == 0


class TestCalculateTimeout:
    """Tests for _calculate_timeout method."""

    def test_minimum_timeout_for_zero_duration(self, whisper_service_instance):
        """Test minimum timeout for zero or negative duration."""
        timeout = whisper_service_instance._calculate_timeout(0)
        assert timeout == 300

    def test_minimum_timeout_for_negative_duration(self, whisper_service_instance):
        """Test minimum timeout for negative duration."""
        timeout = whisper_service_instance._calculate_timeout(-10)
        assert timeout == 300

    def test_gpu_timeout_calculation(self, whisper_service_instance):
        """Test timeout calculation for GPU device."""
        whisper_service_instance.device = "cuda"

        timeout = whisper_service_instance._calculate_timeout(3600)  # 1 hour

        # GPU: 0.5x + 300 minimum
        expected = int(3600 * 0.5 + 300)
        assert timeout == expected

    def test_cpu_timeout_calculation(self, whisper_service_instance):
        """Test timeout calculation for CPU device."""
        whisper_service_instance.device = "cpu"

        timeout = whisper_service_instance._calculate_timeout(3600)  # 1 hour

        # CPU: 2x + 300 minimum
        expected = int(3600 * 2 + 300)
        assert timeout == expected

    def test_short_audio_timeout(self, whisper_service_instance):
        """Test timeout for short audio file."""
        timeout = whisper_service_instance._calculate_timeout(60)  # 1 minute

        assert timeout >= 300  # Minimum timeout


class TestSecondsToSrtTime:
    """Tests for _seconds_to_srt_time method."""

    def test_convert_zero_seconds(self, whisper_service_instance):
        """Test converting zero seconds."""
        result = whisper_service_instance._seconds_to_srt_time(0)
        assert result == "00:00:00,000"

    def test_convert_seconds_only(self, whisper_service_instance):
        """Test converting seconds with no minutes."""
        result = whisper_service_instance._seconds_to_srt_time(45.678)
        assert result == "00:00:45,677"  # Floating point precision

    def test_convert_minutes_and_seconds(self, whisper_service_instance):
        """Test converting minutes and seconds."""
        result = whisper_service_instance._seconds_to_srt_time(125.5)  # 2:05.5
        assert result == "00:02:05,500"

    def test_convert_hours_minutes_seconds(self, whisper_service_instance):
        """Test converting hours, minutes, and seconds."""
        result = whisper_service_instance._seconds_to_srt_time(3661.234)  # 1:01:01.234
        assert result == "01:01:01,233"  # Floating point precision

    def test_convert_full_hour(self, whisper_service_instance):
        """Test converting exactly one hour."""
        result = whisper_service_instance._seconds_to_srt_time(3600.0)
        assert result == "01:00:00,000"

    def test_millisecond_rounding(self, whisper_service_instance):
        """Test millisecond rounding."""
        result = whisper_service_instance._seconds_to_srt_time(1.9999)
        assert result == "00:00:01,999"


class TestSegmentsToDict:
    """Tests for _segments_to_dict method."""

    def test_convert_segments_to_dict(self, whisper_service_instance):
        """Test converting segments to dictionary format."""
        mock_segment = Mock()
        mock_segment.start = 10.5
        mock_segment.end = 15.75
        mock_segment.text = "  Test text with spaces  "

        result = whisper_service_instance._segments_to_dict([mock_segment])

        assert len(result) == 1
        assert result[0]["start"] == "00:00:10,500"
        assert result[0]["end"] == "00:00:15,750"
        assert result[0]["text"] == "Test text with spaces"

    def test_convert_multiple_segments(self, whisper_service_instance):
        """Test converting multiple segments."""
        segments = [
            Mock(start=0.0, end=1.0, text="First"),
            Mock(start=1.0, end=2.0, text="Second"),
            Mock(start=2.0, end=3.0, text="Third"),
        ]

        result = whisper_service_instance._segments_to_dict(segments)

        assert len(result) == 3
        assert result[0]["text"] == "First"
        assert result[1]["text"] == "Second"
        assert result[2]["text"] == "Third"

    def test_empty_segments_list(self, whisper_service_instance):
        """Test handling empty segments list."""
        result = whisper_service_instance._segments_to_dict([])
        assert result == []


class TestTranscribeStandard:
    """Tests for _transcribe_standard method."""

    def test_successful_standard_transcription(self, whisper_service_instance):
        """Test successful standard transcription."""
        result = whisper_service_instance._transcribe_standard(
            "/path/to/audio.mp3",
            None,
            None,
            "test-id"
        )

        assert "text" in result
        assert "segments" in result
        assert "language" in result
        assert "duration" in result
        assert result["language"] == "en"

    def test_cancellation_before_transcription(self, whisper_service_instance):
        """Test cancellation before transcription starts."""
        cancel_event = Event()
        cancel_event.set()

        with pytest.raises(Exception, match="cancelled"):
            whisper_service_instance._transcribe_standard(
                "/path/to/audio.mp3",
                None,
                cancel_event,
                "test-id"
            )

    def test_transcription_error_handling(self, whisper_service_instance):
        """Test handling of transcription errors."""
        whisper_service_instance.model.transcribe.side_effect = Exception("Transcription failed")

        with pytest.raises(Exception, match="Transcription failed"):
            whisper_service_instance._transcribe_standard(
                "/path/to/audio.mp3",
                None,
                None,
                "test-id"
            )


class TestRunFasterWhisper:
    """Tests for _run_faster_whisper method."""

    def test_successful_whisper_execution(self, whisper_service_instance, mock_whisper_model):
        """Test successful faster-whisper execution."""
        mock_segments = [
            Mock(text="Test", start=0.0, end=1.0),
            Mock(text="segment", start=1.0, end=2.0),
        ]
        mock_info = Mock(language="zh", language_probability=0.9, duration=2.0)

        mock_whisper_model.transcribe.return_value = (iter(mock_segments), mock_info)

        segments, info = whisper_service_instance._run_faster_whisper(
            "/path/to/audio.mp3",
            None,
            "test-id"
        )

        result_list = list(segments)
        assert len(result_list) == 2
        assert info.language == "zh"

    def test_cancellation_during_transcription(self, whisper_service_instance, mock_whisper_model):
        """Test cancellation during segment iteration."""
        cancel_event = Event()

        def segment_generator():
            yield Mock(text="First", start=0.0, end=1.0)
            cancel_event.set()  # Set cancel after first segment
            yield Mock(text="Second", start=1.0, end=2.0)

        mock_whisper_model.transcribe.return_value = (segment_generator(), Mock(language="en"))

        with pytest.raises(Exception, match="cancelled"):
            whisper_service_instance._run_faster_whisper(
                "/path/to/audio.mp3",
                cancel_event,
                "test-id"
            )

    def test_cancellation_before_transcription(self, whisper_service_instance):
        """Test cancellation set before transcription starts."""
        cancel_event = Event()
        cancel_event.set()

        with pytest.raises(Exception, match="cancelled"):
            whisper_service_instance._run_faster_whisper(
                "/path/to/audio.mp3",
                cancel_event,
                "test-id"
            )


class TestTranscribe:
    """Tests for transcribe method (main entry point)."""

    def test_short_audio_uses_standard_transcription(self, whisper_service_instance):
        """Test that short audio uses standard (non-chunked) transcription."""
        with patch.object(whisper_service_instance, '_get_audio_duration', return_value=300):
            with patch.object(whisper_service_instance, '_transcribe_standard') as mock_standard:
                mock_standard.return_value = {"text": "test", "segments": [], "language": "en"}

                result = whisper_service_instance.transcribe("/path/to/audio.mp3")

                mock_standard.assert_called_once()
                assert "text" in result

    def test_long_audio_with_chunking_enabled(self, whisper_service_instance):
        """Test that long audio uses chunked transcription when enabled."""
        with patch('app.services.whisper_service.settings') as mock_settings:
            mock_settings.ENABLE_CHUNKING = True
            mock_settings.CHUNK_SIZE_MINUTES = 10

            with patch.object(whisper_service_instance, '_get_audio_duration', return_value=900):  # 15 min
                with patch.object(whisper_service_instance, 'transcribe_with_chunking') as mock_chunking:
                    mock_chunking.return_value = {"text": "chunked", "segments": [], "language": "zh"}

                    result = whisper_service_instance.transcribe("/path/to/audio.mp3")

                    mock_chunking.assert_called_once()

    def test_long_audio_with_chunking_disabled(self, whisper_service_instance):
        """Test that audio uses standard transcription when chunking disabled."""
        with patch('app.services.whisper_service.settings') as mock_settings:
            mock_settings.ENABLE_CHUNKING = False

            with patch.object(whisper_service_instance, '_get_audio_duration', return_value=3600):
                with patch.object(whisper_service_instance, '_transcribe_standard') as mock_standard:
                    mock_standard.return_value = {"text": "test", "segments": [], "language": "en"}

                    result = whisper_service_instance.transcribe("/path/to/audio.mp3")

                    mock_standard.assert_called_once()

    def test_cancellation_before_start(self, whisper_service_instance):
        """Test cancellation before transcription starts."""
        cancel_event = Event()
        cancel_event.set()

        with pytest.raises(Exception, match="cancelled"):
            whisper_service_instance.transcribe(
                "/path/to/audio.mp3",
                None,
                cancel_event,
                "test-id"
            )


class TestAddTimeOffset:
    """Tests for _add_time_offset method."""

    def test_add_offset_to_timestamp(self, whisper_service_instance):
        """Test adding offset to SRT timestamp."""
        result = whisper_service_instance._add_time_offset("00:00:10,000", 5.5)
        assert result == "00:00:15,500"

    def test_add_offset_across_minute_boundary(self, whisper_service_instance):
        """Test adding offset that crosses minute boundary."""
        result = whisper_service_instance._add_time_offset("00:00:58,000", 5.0)
        assert result == "00:01:03,000"

    def test_add_offset_across_hour_boundary(self, whisper_service_instance):
        """Test adding offset that crosses hour boundary."""
        result = whisper_service_instance._add_time_offset("00:59:58,000", 5.0)
        assert result == "01:00:03,000"

    def test_add_large_offset(self, whisper_service_instance):
        """Test adding large time offset."""
        result = whisper_service_instance._add_time_offset("00:00:00,000", 3665.0)  # 1:01:05
        assert result == "01:01:05,000"

    def test_invalid_timestamp_format(self, whisper_service_instance):
        """Test handling of invalid timestamp format."""
        result = whisper_service_instance._add_time_offset("invalid", 10.0)
        assert result == "invalid"

    def test_negative_offset_clips_to_zero(self, whisper_service_instance):
        """Test that negative offset clips to zero."""
        result = whisper_service_instance._add_time_offset("00:00:10,000", -15.0)
        assert result == "00:00:00,000"


class TestParseSrtTime:
    """Tests for _parse_srt_time method."""

    def test_parse_seconds_only(self, whisper_service_instance):
        """Test parsing timestamp with seconds only."""
        result = whisper_service_instance._parse_srt_time("00:00:45,500")
        assert result == 45.5

    def test_parse_minutes_and_seconds(self, whisper_service_instance):
        """Test parsing timestamp with minutes."""
        result = whisper_service_instance._parse_srt_time("00:02:30,000")
        assert result == 150.0

    def test_parse_hours_minutes_seconds(self, whisper_service_instance):
        """Test parsing full timestamp."""
        result = whisper_service_instance._parse_srt_time("01:15:30,500")
        assert result == 4530.5

    def test_parse_invalid_format(self, whisper_service_instance):
        """Test handling of invalid format."""
        result = whisper_service_instance._parse_srt_time("invalid")
        assert result == 0.0

    def test_parse_with_milliseconds(self, whisper_service_instance):
        """Test parsing with milliseconds."""
        result = whisper_service_instance._parse_srt_time("00:00:00,999")
        assert result == 0.999


class TestExtractAudioSegment:
    """Tests for _extract_audio_segment method."""

    def test_extract_segment_success(self, whisper_service_instance):
        """Test successful audio segment extraction."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout="", stderr="")

            whisper_service_instance._extract_audio_segment(
                "/input/audio.mp3",
                "/output/segment.wav",
                10.0,
                20.0
            )

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "ffmpeg"

    def test_extract_segment_failure(self, whisper_service_instance):
        """Test handling of extraction failure."""
        import subprocess

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

            with pytest.raises(Exception):
                whisper_service_instance._extract_audio_segment(
                    "/input/audio.mp3",
                    "/output/segment.wav",
                    10.0,
                    20.0
                )


class TestMergeWithTimestamps:
    """Tests for _merge_with_timestamps method."""

    def test_merge_two_chunks(self, whisper_service_instance):
        """Test merging two chunks with timestamps."""
        chunks_results = [
            {
                "text": "First chunk",
                "segments": [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "First"}],
                "language": "en"
            },
            {
                "text": "Second chunk",
                "segments": [{"start": "00:00:05,000", "end": "00:00:10,000", "text": "Second"}],
                "language": "en"
            }
        ]

        result = whisper_service_instance._merge_with_timestamps(chunks_results)

        assert "First chunk" in result["text"]
        assert "Second chunk" in result["text"]
        assert len(result["segments"]) == 2

    def test_merge_with_failed_chunk(self, whisper_service_instance):
        """Test merging when one chunk failed."""
        chunks_results = [
            {
                "text": "Success",
                "segments": [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "Text"}],
                "language": "en"
            },
            {
                "text": "",
                "segments": [],
                "error": "Failed"
            }
        ]

        result = whisper_service_instance._merge_with_timestamps(chunks_results)

        assert "Success" in result["text"]
        assert len(result["segments"]) == 1

    def test_merge_empty_chunks(self, whisper_service_instance):
        """Test merging empty chunks list."""
        result = whisper_service_instance._merge_with_timestamps([])
        assert result["text"] == ""
        assert result["segments"] == []


class TestExtractTextInTimeWindow:
    """Tests for _extract_text_in_time_window method."""

    def test_extract_text_in_window(self, whisper_service_instance):
        """Test extracting text within time window."""
        chunk_result = {
            "segments": [
                {"start": "00:00:00,000", "end": "00:00:05,000", "text": "Before"},
                {"start": "00:00:10,000", "end": "00:00:15,000", "text": "Inside"},
                {"start": "00:00:20,000", "end": "00:00:25,000", "text": "After"},
            ]
        }

        result = whisper_service_instance._extract_text_in_time_window(chunk_result, 8.0, 12.0)

        assert "Inside" in result
        assert "Before" not in result
        assert "After" not in result

    def test_extract_text_no_segments_in_window(self, whisper_service_instance):
        """Test when no segments are in the time window."""
        chunk_result = {
            "segments": [
                {"start": "00:00:00,000", "end": "00:00:05,000", "text": "Before"},
            ]
        }

        result = whisper_service_instance._extract_text_in_time_window(chunk_result, 10.0, 20.0)

        assert result == ""


class TestMergeWithLcsText:
    """Tests for _merge_with_lcs_text method."""

    def test_merge_with_overlap(self, whisper_service_instance):
        """Test merging text with overlap."""
        prev_overlap = "common text at end"
        curr_overlap = "common text at end and more"
        prev_full = "This is the first chunk. common text at end"
        curr_full = "common text at end and more content from second chunk"

        result = whisper_service_instance._merge_with_lcs_text(
            prev_overlap, curr_overlap, prev_full, curr_full
        )

        # Should deduplicate the common part
        assert "content from second chunk" in result

    def test_merge_without_overlap(self, whisper_service_instance):
        """Test merging text without overlap."""
        prev_overlap = "first chunk text"
        curr_overlap = "second chunk text"
        prev_full = "This is the first chunk text"
        curr_full = "This is the second chunk text"

        result = whisper_service_instance._merge_with_lcs_text(
            prev_overlap, curr_overlap, prev_full, curr_full
        )

        # Should just concatenate
        assert result == " " + curr_full

    def test_merge_with_small_overlap(self, whisper_service_instance):
        """Test merging with very small overlap (below threshold)."""
        prev_overlap = "abc"
        curr_overlap = "def"
        prev_full = "Full text abc"
        curr_full = "def full text"

        result = whisper_service_instance._merge_with_lcs_text(
            prev_overlap, curr_overlap, prev_full, curr_full
        )

        # Small overlap should be ignored
        assert result == " " + curr_full


class TestSingletonInstance:
    """Tests for singleton instance."""

    def test_whisper_service_is_transcribe_service(self):
        """Test that whisper_service is an alias for transcribe_service."""
        from app.services.whisper_service import transcribe_service
        assert whisper_service is transcribe_service
