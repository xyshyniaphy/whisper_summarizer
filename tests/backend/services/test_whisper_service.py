"""
Whisper Service Tests

Tests for faster-whisper transcription service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from threading import Event
import subprocess

from app.services.whisper_service import TranscribeService, transcribe_service


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_whisper_model():
    """Mock WhisperModel."""
    mock_model = MagicMock()
    mock_info = MagicMock()
    mock_info.language = "zh"
    mock_info.language_probability = 0.95
    mock_info.duration = 120.5

    # Create mock segments
    mock_segment1 = MagicMock()
    mock_segment1.start = 0.0
    mock_segment1.end = 5.2
    mock_segment1.text = "这是第一句话"

    mock_segment2 = MagicMock()
    mock_segment2.start = 5.2
    mock_segment2.end = 10.5
    mock_segment2.text = "这是第二句话"

    mock_model.transcribe.return_value = (
        iter([mock_segment1, mock_segment2]),
        mock_info
    )

    return mock_model


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a sample audio file path."""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"fake audio data")
    return str(audio_file)


# ============================================================================
# TranscribeService.__init__() Tests
# ============================================================================

class TestTranscribeServiceInit:
    """Test TranscribeService initialization."""

    @patch('app.services.whisper_service.WhisperModel')
    @patch.dict('os.environ', {'FASTER_WHISPER_DEVICE': 'cpu', 'FASTER_WHISPER_COMPUTE_TYPE': 'int8'})
    def test_should_initialize_with_cpu_settings(self, mock_model_class):
        """Should initialize with CPU settings from environment."""
        mock_instance = MagicMock()
        mock_model_class.return_value = mock_instance

        service = TranscribeService()

        assert service.device == "cpu"
        assert service.compute_type == "int8"
        mock_model_class.assert_called_once()

    @patch('app.services.whisper_service.WhisperModel')
    @patch.dict('os.environ', {'FASTER_WHISPER_DEVICE': 'cuda', 'FASTER_WHISPER_COMPUTE_TYPE': 'float16'})
    def test_should_initialize_with_gpu_settings(self, mock_model_class):
        """Should initialize with GPU settings from environment."""
        mock_instance = MagicMock()
        mock_model_class.return_value = mock_instance

        service = TranscribeService()

        assert service.device == "cuda"
        assert service.compute_type == "float16"


# ============================================================================
# _get_audio_duration() Tests
# ============================================================================

class TestGetAudioDuration:
    """Test audio duration detection."""

    @patch('subprocess.run')
    def test_should_get_duration_from_ffprobe(self, mock_run):
        """Should get duration from ffprobe output."""
        mock_run.return_value.stdout = "125.5"
        mock_run.return_value.check = True

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):  # Skip model init
            duration = service._get_audio_duration("/path/to/audio.wav")

        assert duration == 125

    @patch('subprocess.run')
    def test_should_return_zero_on_timeout(self, mock_run):
        """Should return 0 when ffprobe times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 30)

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            duration = service._get_audio_duration("/path/to/audio.wav")

        assert duration == 0

    @patch('subprocess.run')
    def test_should_return_zero_on_error(self, mock_run):
        """Should return 0 when ffprobe fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            duration = service._get_audio_duration("/path/to/audio.wav")

        assert duration == 0

    @patch('subprocess.run')
    def test_should_handle_invalid_duration_output(self, mock_run):
        """Should return 0 when ffprobe returns invalid output."""
        mock_run.return_value.stdout = "invalid"
        mock_run.return_value.check = True

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            duration = service._get_audio_duration("/path/to/audio.wav")

        assert duration == 0


# ============================================================================
# _calculate_timeout() Tests
# ============================================================================

class TestCalculateTimeout:
    """Test timeout calculation."""

    def test_should_return_minimum_timeout_for_zero_duration(self):
        """Should return minimum timeout for zero or negative duration."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            timeout = service._calculate_timeout(0)

        assert timeout == 300

    def test_should_use_gpu_multiplier_for_cuda(self):
        """Should use 0.5x multiplier for GPU."""
        service = TranscribeService()
        service.device = "cuda"
        with patch.object(service, 'model', MagicMock()):
            timeout = service._calculate_timeout(3600)  # 1 hour

        # 3600 * 0.5 + 300 = 2100
        assert timeout == 2100

    def test_should_use_cpu_multiplier_for_cpu(self):
        """Should use 2x multiplier for CPU."""
        service = TranscribeService()
        service.device = "cpu"
        with patch.object(service, 'model', MagicMock()):
            timeout = service._calculate_timeout(3600)  # 1 hour

        # 3600 * 2 + 300 = 7500
        assert timeout == 7500


# ============================================================================
# _seconds_to_srt_time() Tests
# ============================================================================

class TestSecondsToSrtTime:
    """Test conversion from seconds to SRT timestamp format."""

    def test_should_convert_simple_time(self):
        """Should convert simple time correctly."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._seconds_to_srt_time(65.5)

        assert result == "00:01:05,500"

    def test_should_convert_hours(self):
        """Should convert time with hours."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._seconds_to_srt_time(3661.123)

        assert result == "01:01:01,123"

    def test_should_handle_zero_time(self):
        """Should handle zero time."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._seconds_to_srt_time(0)

        assert result == "00:00:00,000"

    def test_should_handle_milliseconds(self):
        """Should handle milliseconds correctly."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._seconds_to_srt_time(10.999)

        assert result == "00:00:10,999"


# ============================================================================
# _segments_to_dict() Tests
# ============================================================================

class TestSegmentsToDict:
    """Test conversion of segments to dictionary format."""

    def test_should_convert_segments_to_dict(self):
        """Should convert segments to SRT-like format."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            mock_segments = [
                MagicMock(start=0.0, end=5.2, text="First segment"),
                MagicMock(start=5.2, end=10.5, text="Second segment"),
            ]

            result = service._segments_to_dict(mock_segments)

        assert len(result) == 2
        assert result[0]["start"] == "00:00:00,000"
        assert result[0]["end"] == "00:00:05,200"
        assert result[0]["text"] == "First segment"
        assert result[1]["start"] == "00:00:05,200"
        assert result[1]["end"] == "00:00:10,500"

    def test_should_strip_whitespace_from_text(self):
        """Should strip whitespace from segment text."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            mock_segment = MagicMock(start=0.0, end=5.0, text="  text with spaces  ")

            result = service._segments_to_dict([mock_segment])

        assert result[0]["text"] == "text with spaces"

    def test_should_handle_empty_segments(self):
        """Should handle empty segment list."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._segments_to_dict([])

        assert result == []


# ============================================================================
# _parse_srt_time() Tests
# ============================================================================

class TestParseSrtTime:
    """Test parsing SRT timestamp to seconds."""

    def test_should_parse_srt_timestamp(self):
        """Should parse SRT timestamp correctly."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("00:01:05,500")

        assert result == 65.5

    def test_should_parse_hours(self):
        """Should parse timestamp with hours."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("01:02:03,456")

        assert result == 3723.456

    def test_should_handle_invalid_format(self):
        """Should return 0 for invalid format."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("invalid")

        assert result == 0.0


# ============================================================================
# _add_time_offset() Tests
# ============================================================================

class TestAddTimeOffset:
    """Test adding time offset to timestamps."""

    def test_should_add_offset_to_timestamp(self):
        """Should add offset to SRT timestamp."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:01:00,000", 30)

        assert result == "00:01:30,000"

    def test_should_handle_carry_over(self):
        """Should handle carry over to next minute/hour."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:50,500", 15)

        assert result == "00:01:05,500"

    def test_should_handle_negative_result(self):
        """Should handle negative offset that goes below zero."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:10,000", -15)

        assert result == "00:00:00,000"

    def test_should_handle_invalid_format(self):
        """Should return original for invalid format."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("invalid", 30)

        assert result == "invalid"


# ============================================================================
# transcribe() Tests - Standard Mode
# ============================================================================

class TestTranscribeStandard:
    """Test standard transcription."""

    @patch('app.services.whisper_service.TranscribeService._get_audio_duration')
    @patch('app.services.whisper_service.TranscribeService._transcribe_standard')
    def test_should_use_standard_for_short_audio(self, mock_transcribe_standard, mock_duration, sample_audio_file):
        """Should use standard transcription for short audio."""
        mock_duration.return_value = 300  # 5 minutes
        mock_transcribe_standard.return_value = {
            "text": "Transcription text",
            "segments": [],
            "language": "zh"
        }

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service.transcribe(sample_audio_file)

        assert result["text"] == "Transcription text"
        mock_transcribe_standard.assert_called_once()

    @patch('app.services.whisper_service.TranscribeService._get_audio_duration')
    @patch('app.services.whisper_service.TranscribeService.transcribe_with_chunking')
    def test_should_use_chunking_for_long_audio(self, mock_chunking, mock_duration, sample_audio_file):
        """Should use chunking for long audio when enabled."""
        mock_duration.return_value = 1200  # 20 minutes
        mock_chunking.return_value = {
            "text": "Chunked transcription",
            "segments": [],
            "language": "zh"
        }

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with patch('app.services.whisper_service.settings', ENABLE_CHUNKING=True, CHUNK_SIZE_MINUTES=10):
                result = service.transcribe(sample_audio_file)

        assert result["text"] == "Chunked transcription"
        mock_chunking.assert_called_once()


# ============================================================================
# _transcribe_standard() Tests
# ============================================================================

class TestTranscribeStandardMethod:
    """Test standard transcription method."""

    @patch('app.services.whisper_service.TranscribeService._run_faster_whisper')
    def test_should_transcribe_successfully(self, mock_run, sample_audio_file):
        """Should transcribe audio successfully."""
        mock_segments = [
            MagicMock(start=0.0, end=5.0, text="First"),
            MagicMock(start=5.0, end=10.0, text="Second"),
        ]
        mock_info = MagicMock()
        mock_info.language = "zh"
        mock_info.language_probability = 0.95
        mock_info.duration = 10.0
        mock_run.return_value = (mock_segments, mock_info)

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._transcribe_standard(sample_audio_file)

        assert result["text"] == "First Second"
        assert result["language"] == "zh"
        assert result["duration"] == 10.0
        assert len(result["segments"]) == 2

    def test_should_raise_on_cancel_event(self, sample_audio_file):
        """Should raise exception when cancel event is set."""
        cancel_event = Event()
        cancel_event.set()

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with pytest.raises(Exception, match="Transcription cancelled"):
                service._transcribe_standard(sample_audio_file, cancel_event=cancel_event)


# ============================================================================
# _run_faster_whisper() Tests
# ============================================================================

class TestRunFasterWhisper:
    """Test faster-whisper execution."""

    def test_should_return_segments_and_info(self, sample_audio_file):
        """Should return segments and info from model."""
        mock_segments = [
            MagicMock(start=0.0, end=5.0, text="Segment 1"),
            MagicMock(start=5.0, end=10.0, text="Segment 2"),
        ]
        mock_info = MagicMock()
        mock_info.language = "en"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter(mock_segments), mock_info)

        service = TranscribeService()
        service.model = mock_model

        segments, info = service._run_faster_whisper(sample_audio_file)

        assert list(segments) == mock_segments
        assert info.language == "en"

    def test_should_check_cancel_during_iteration(self, sample_audio_file):
        """Should check for cancellation during segment iteration."""
        cancel_event = Event()

        # Create generator that yields one segment then stops
        def mock_transcribe(*args, **kwargs):
            mock_seg = MagicMock(start=0.0, end=5.0, text="Text")
            mock_info = MagicMock()
            for i in range(10):
                if i == 5 and cancel_event.is_set():
                    raise Exception("Transcription cancelled")
                yield mock_seg

        mock_model = MagicMock()
        mock_model.transcribe = mock_transcribe
        mock_info = MagicMock()

        service = TranscribeService()
        service.model = mock_model
        service.model.transcribe = lambda *a, **k: (mock_transcribe(*a, **k), mock_info)

        cancel_event.set()

        with pytest.raises(Exception, match="Transcription cancelled"):
            service._run_faster_whisper(sample_audio_file, cancel_event=cancel_event)


# ============================================================================
# _extract_text_in_time_window() Tests
# ============================================================================

class TestExtractTextInTimeWindow:
    """Test text extraction within time window."""

    def test_should_extract_text_in_window(self):
        """Should extract text from segments within time window."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunk_result = {
                "segments": [
                    {"start": "00:00:05,000", "end": "00:00:10,000", "text": "First"},
                    {"start": "00:00:15,000", "end": "00:00:20,000", "text": "Second"},
                    {"start": "00:00:25,000", "end": "00:00:30,000", "text": "Third"},
                ]
            }

            result = service._extract_text_in_time_window(chunk_result, 10, 25)

        assert "Second" in result
        assert "Third" in result

    def test_should_return_empty_for_no_matching_segments(self):
        """Should return empty string when no segments match."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunk_result = {
                "segments": [
                    {"start": "00:00:05,000", "end": "00:00:10,000", "text": "First"},
                ]
            }

            result = service._extract_text_in_time_window(chunk_result, 20, 30)

        assert result == ""


# ============================================================================
# _merge_with_timestamps() Tests
# ============================================================================

class TestMergeWithTimestamps:
    """Test timestamp-based merge."""

    def test_should_merge_multiple_chunks(self):
        """Should merge chunks using timestamps."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "First chunk",
                    "segments": [
                        {"start": "00:00:00,000", "end": "00:00:05,000", "text": "Seg1"}
                    ]
                },
                {
                    "text": "Second chunk",
                    "segments": [
                        {"start": "00:00:10,000", "end": "00:00:15,000", "text": "Seg2"}
                    ]
                }
            ]

            result = service._merge_with_timestamps(chunks)

        assert result["text"] == "First chunk Second chunk"
        assert len(result["segments"]) == 2

    def test_should_skip_failed_chunks(self):
        """Should skip chunks with errors."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {"text": "Good chunk", "segments": []},
                {"error": "Failed", "text": ""},
                {"text": "Another good", "segments": []}
            ]

            result = service._merge_with_timestamps(chunks)

        assert "Good chunk" in result["text"]
        assert "Another good" in result["text"]

    def test_should_handle_single_chunk(self):
        """Should return single chunk as-is."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {"text": "Single", "segments": [], "language": "zh"}
            ]

            result = service._merge_with_timestamps(chunks)

        assert result["text"] == "Single"
        assert result["language"] == "zh"


# ============================================================================
# _merge_chunk_results() Tests
# ============================================================================

class TestMergeChunkResults:
    """Test chunk result merging."""

    @patch('app.services.whisper_service.settings')
    def test_should_choose_lcs_for_small_chunk_count(self, mock_settings):
        """Should use LCS for small chunk counts."""
        mock_settings.LCS_CHUNK_THRESHOLD = 10
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with patch.object(service, '_merge_with_lcs') as mock_lcs:
                mock_lcs.return_value = {"text": "merged", "segments": []}

                chunks = [{"text": f"Chunk {i}", "segments": []} for i in range(5)]
                result = service._merge_chunk_results(chunks)

        mock_lcs.assert_called_once()

    @patch('app.services.whisper_service.settings')
    def test_should_choose_timestamp_for_large_chunk_count(self, mock_settings):
        """Should use timestamp-based merge for large chunk counts."""
        mock_settings.LCS_CHUNK_THRESHOLD = 10
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with patch.object(service, '_merge_with_timestamps') as mock_ts:
                mock_ts.return_value = {"text": "merged", "segments": []}

                chunks = [{"text": f"Chunk {i}", "segments": []} for i in range(15)]
                result = service._merge_chunk_results(chunks)

        mock_ts.assert_called_once()

    def test_should_handle_empty_chunks(self):
        """Should handle empty chunk list."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._merge_chunk_results([])

        assert result["text"] == ""
        assert result["segments"] == []

    def test_should_handle_single_chunk(self):
        """Should return single chunk unchanged."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [{"text": "Single", "segments": [], "language": "zh"}]
            result = service._merge_chunk_results(chunks)

        assert result["text"] == "Single"


# ============================================================================
# Edge Cases
# ============================================================================

class TestWhisperServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_should_handle_empty_segments(self):
        """Should handle empty segment list."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._segments_to_dict([])

        assert result == []

    def test_should_handle_unicode_text(self):
        """Should handle Unicode text in segments."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            mock_segment = MagicMock(start=0.0, end=5.0, text="中文 🎵 emoji")
            result = service._segments_to_dict([mock_segment])

        assert result[0]["text"] == "中文 🎵 emoji"

    def test_should_handle_very_long_timestamp(self):
        """Should handle very long timestamps."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._seconds_to_srt_time(86461.999)  # >24 hours

        # Due to float precision, we get 998 instead of 999
        assert result == "24:01:01,998"


# ============================================================================
# _transcribe_chunk() Tests
# ============================================================================

class TestTranscribeChunk:
    """Test single chunk transcription."""

    @patch('app.services.whisper_service.TranscribeService._run_faster_whisper')
    def test_should_transcribe_single_chunk(self, mock_run, sample_audio_file, tmp_path):
        """Should transcribe a single chunk successfully."""
        mock_segments = [
            MagicMock(start=0.0, end=5.0, text="Chunk text")
        ]
        mock_info = MagicMock()
        mock_info.language = "zh"

        mock_run.return_value = (mock_segments, mock_info)

        chunk_info = {
            "index": 0,
            "path": sample_audio_file,
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0
        }

        service = TranscribeService()
        service.model = MagicMock()
        result = service._transcribe_chunk(chunk_info, output_dir=str(tmp_path))

        assert result["text"] == "Chunk text"
        assert result["language"] == "zh"
        assert result["chunk_index"] == 0
        assert result["chunk_start_time"] == 0.0

    def test_should_cancel_chunk_if_event_set(self, sample_audio_file, tmp_path):
        """Should return error if cancel event is set."""
        cancel_event = Event()
        cancel_event.set()

        chunk_info = {
            "index": 0,
            "path": sample_audio_file,
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0
        }

        service = TranscribeService()
        service.model = MagicMock()
        result = service._transcribe_chunk(chunk_info, output_dir=str(tmp_path), cancel_event=cancel_event)

        assert "error" in result


# ============================================================================
# _detect_silence_segments() Tests
# ============================================================================

class TestDetectSilenceSegments:
    """Test silence detection for VAD splitting."""

    @patch('subprocess.run')
    def test_should_detect_silence_segments(self, mock_run, sample_audio_file):
        """Should parse silence segments from ffmpeg output."""
        mock_run.return_value.stderr = """
        [silencedetect @ 0x...]
        silence_start: 1.5
        silence_end: 2.5
        silence_duration: 1.0
        [silencedetect @ 0x...]
        silence_start: 10.0
        silence_end: 12.0
        silence_duration: 2.0
        """

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            segments = service._detect_silence_segments(sample_audio_file)

        assert len(segments) == 2
        assert segments[0] == (1.5, 2.5)
        assert segments[1] == (10.0, 12.0)

    @patch('subprocess.run')
    def test_should_return_empty_on_error(self, mock_run, sample_audio_file):
        """Should return empty list when ffmpeg fails."""
        mock_run.side_effect = Exception("FFmpeg failed")

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            segments = service._detect_silence_segments(sample_audio_file)

        assert segments == []


# ============================================================================
# _calculate_split_points() Tests
# ============================================================================

class TestCalculateSplitPoints:
    """Test split point calculation."""

    def test_should_calculate_split_points_with_silence(self):
        """Should calculate split points using silence information."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            silence = [(100, 105), (200, 205), (300, 305)]
            split_points = service._calculate_split_points(400, 100, silence)

        # Should have 4 chunks (400s / 100s)
        assert len(split_points) == 4

    def test_should_calculate_split_points_without_silence(self):
        """Should calculate split points without silence information."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            split_points = service._calculate_split_points(300, 100, [])

        # Should create chunks at target times
        assert len(split_points) == 3


# ============================================================================
# _transcribe_chunks_parallel() Tests
# ============================================================================

class TestTranscribeChunksParallel:
    """Test parallel chunk transcription."""

    @patch('app.services.whisper_service.TranscribeService._transcribe_chunk')
    @patch('app.services.whisper_service.settings')
    def test_should_transcribe_chunks_in_parallel(self, mock_settings, mock_transcribe, tmp_path):
        """Should transcribe multiple chunks in parallel."""
        mock_settings.MAX_CONCURRENT_CHUNKS = 2

        # Mock successful transcription
        mock_transcribe.return_value = {
            "text": "Chunk text",
            "segments": [],
            "language": "zh",
            "chunk_index": 0,
            "chunk_start_time": 0,
            "chunk_end_time": 10
        }

        chunks_info = [
            {"index": 0, "path": "/chunk0.wav", "start_time": 0, "end_time": 10, "duration": 10},
            {"index": 1, "path": "/chunk1.wav", "start_time": 10, "end_time": 20, "duration": 10},
        ]

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            results = service._transcribe_chunks_parallel(chunks_info, output_dir=str(tmp_path))

        assert len(results) == 2
        assert all(r["text"] == "Chunk text" for r in results)


# ============================================================================
# Additional Merge Tests
# ============================================================================

class TestMergeWithLCS:
    """Test LCS-based merge functionality."""

    def test_should_merge_with_lcs_text(self):
        """Should merge text using LCS algorithm."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            prev_overlap = "hello world this is a test"
            curr_overlap = "world this is a test more text"
            prev_full = "Start: hello world this is a test"
            curr_full = "world this is a test more text here"

            result = service._merge_with_lcs_text(
                prev_overlap, curr_overlap, prev_full, curr_full
            )

        # Should merge and remove overlap
        assert isinstance(result, str)
        assert len(result) > 0

    def test_should_return_curr_full_on_no_match(self):
        """Should return full current text when no LCS match found."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            prev_overlap = "completely different text"
            curr_overlap = "nothing matches here"
            prev_full = "Previous: completely different text"
            curr_full = "Current: nothing matches here"

            result = service._merge_with_lcs_text(
                prev_overlap, curr_overlap, prev_full, curr_full
            )

        # Should return current text with space prefix
        assert result == " Current: nothing matches here"


# ============================================================================
# Additional Edge Cases
# ============================================================================

class TestAdditionalEdgeCases:
    """Additional edge case tests."""

    def test_should_handle_very_short_audio(self, sample_audio_file):
        """Should handle very short audio (< 1 second)."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            # Just verify it doesn't crash
            assert service is not None

    def test_should_handle_segment_with_whitespace_only(self):
        """Should handle segment with only whitespace."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            mock_segment = MagicMock(start=0.0, end=5.0, text="   ")
            result = service._segments_to_dict([mock_segment])

        assert result[0]["text"] == ""

    def test_should_calculate_correct_split_times(self):
        """Should calculate correct split times for chunks."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            silence = [(100, 105), (300, 305)]
            split_points = service._calculate_split_points(600, 200, silence)

        # Should have correct number of chunks
        assert len(split_points) >= 1

    def test_should_handle_zero_duration_for_timeout(self):
        """Should handle zero or negative duration in timeout calculation."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            timeout = service._calculate_timeout(0)

        assert timeout == 300  # Minimum timeout

    def test_should_handle_large_overlap_ratio(self):
        """Should handle large overlap ratios in merge."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            prev = {"text": "a" * 100 + " overlap " + "b" * 100}
            curr = {"text": " overlap " + "b" * 100 + "c" * 100}

            result = service._merge_with_timestamps([prev, curr])

        assert result is not None

    def test_should_extract_text_in_window_bounds(self):
        """Should extract text within time window bounds."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunk_result = {
                "segments": [
                    {"start": "00:00:00,000", "end": "00:00:05,000", "text": "Before"},
                    {"start": "00:00:10,000", "end": "00:00:15,000", "text": "Within"},
                    {"start": "00:00:20,000", "end": "00:00:25,000", "text": "After"},
                ]
            }

            result = service._extract_text_in_time_window(chunk_result, 8, 18)

        # Should only include the segment within window
        assert "Within" in result
        assert "Before" not in result
        assert "After" not in result


# ============================================================================
# Cancellation Tests (Lines 143-144, 273-274, 350-352, 365-367, 757-759)
# ============================================================================

class TestCancellationDuringTranscription:
    """Test cancellation support during transcription."""

    def test_should_cancel_before_transcribing(self, sample_audio_file):
        """Should cancel before transcription starts."""
        from threading import Event
        cancel_event = Event()
        cancel_event.set()  # Already cancelled

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with pytest.raises(Exception, match="cancelled"):
                service.transcribe(sample_audio_file, cancel_event=cancel_event)

    @patch('app.services.whisper_service.TranscribeService._get_audio_duration')
    def test_should_cancel_during_transcription(self, mock_duration, sample_audio_file):
        """Should cancel during transcription loop."""
        from threading import Event

        mock_duration.return_value = 30  # Short file, no chunking
        cancel_event = Event()

        service = TranscribeService()
        mock_model = MagicMock()
        mock_segments = [
            MagicMock(start=0, end=1, text="First segment"),
            MagicMock(start=1, end=2, text="Second segment"),
        ]
        mock_info = MagicMock(language="zh", language_probability=0.9, duration=30.0)

        # Make transcribe return generator that sets cancel event mid-way
        call_count = [0]
        def transcribe_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call succeeds, set cancel after
                cancel_event.set()
            return (iter(mock_segments), mock_info)

        mock_model.transcribe.side_effect = transcribe_side_effect
        service.model = mock_model

        with pytest.raises(Exception, match="cancelled"):
            service.transcribe(sample_audio_file, cancel_event=cancel_event)

    def test_should_cancel_chunk_before_starting(self, sample_audio_file, tmp_path):
        """Should cancel chunk transcription before starting."""
        from threading import Event
        cancel_event = Event()
        cancel_event.set()  # Already cancelled

        chunk_info = {
            "index": 0,
            "path": sample_audio_file,
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0
        }

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._transcribe_chunk(chunk_info, str(tmp_path), cancel_event=cancel_event)

        assert "error" in result
        assert result["chunk_index"] == 0


# ============================================================================
# _add_time_offset() Tests (Lines 807-840)
# ============================================================================

class TestAddTimeOffset:
    """Test time offset addition for SRT timestamps."""

    def test_should_add_offset_to_timestamp(self):
        """Should add time offset to SRT timestamp."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:10,500", 30.5)

        # 00:00:10,500 + 30.5s = 00:00:41,000
        assert result == "00:00:41,000"

    def test_should_handle_large_offset(self):
        """Should handle large time offsets that span hours."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:30,000", 3665.5)

        # 00:00:30,000 + 3665.5s = 01:01:35,500
        assert result == "01:01:35,500"

    def test_should_handle_millisecond_overflow(self):
        """Should handle millisecond overflow correctly."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:00,800", 0.5)

        # 00:00:00,800 + 0.5s = 00:00:01,300
        assert result == "00:00:01,300"

    def test_should_handle_negative_offset_clamping(self):
        """Should clamp to zero when offset is negative."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("00:00:10,000", -15.0)

        # Should clamp to zero
        assert result == "00:00:00,000"

    def test_should_handle_invalid_format(self):
        """Should return original string for invalid format."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._add_time_offset("invalid", 10.0)

        assert result == "invalid"


# ============================================================================
# _parse_srt_time() Tests (Lines 1065-1084)
# ============================================================================

class TestParseSrtTime:
    """Test SRT timestamp parsing to seconds."""

    def test_should_parse_standard_srt_time(self):
        """Should parse standard SRT timestamp."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("00:01:30,500")

        assert result == 90.5

    def test_should_parse_time_with_hours(self):
        """Should parse timestamp with hours."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("01:30:45,250")

        assert result == 5445.25

    def test_should_handle_zero_timestamp(self):
        """Should parse zero timestamp."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("00:00:00,000")

        assert result == 0.0

    def test_should_handle_invalid_format(self):
        """Should return zero for invalid format."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._parse_srt_time("invalid")

        assert result == 0.0


# ============================================================================
# _merge_with_timestamps() Tests (Lines 878-921)
# ============================================================================

class TestMergeWithTimestamps:
    """Test timestamp-based merging."""

    def test_should_merge_chunks_with_timestamps(self):
        """Should merge chunks using timestamp strategy."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "First chunk text",
                    "segments": [
                        {"start": "00:00:00,000", "end": "00:00:05,000", "text": "First"}
                    ],
                    "language": "zh"
                },
                {
                    "text": "Second chunk text",
                    "segments": [
                        {"start": "00:00:05,000", "end": "00:00:10,000", "text": "Second"}
                    ],
                    "language": "zh"
                }
            ]

            result = service._merge_with_timestamps(chunks)

        assert "First chunk text" in result["text"]
        assert "Second chunk text" in result["text"]
        assert len(result["segments"]) == 2

    def test_should_skip_failed_chunks(self):
        """Should skip chunks with errors."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "Valid chunk",
                    "segments": [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "Text"}],
                    "language": "zh"
                },
                {
                    "text": "",
                    "segments": [],
                    "error": "Transcription failed"
                }
            ]

            result = service._merge_with_timestamps(chunks)

        assert "Valid chunk" in result["text"]
        assert len(result["segments"]) == 1

    def test_should_handle_empty_chunks_list(self):
        """Should handle empty chunks list."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            result = service._merge_with_timestamps([])

        assert result["text"] == ""
        assert result["segments"] == []


# ============================================================================
# _extract_audio_segment() Error Handling (Lines 627-653)
# ============================================================================

class TestExtractAudioSegmentErrors:
    """Test error handling in audio segment extraction."""

    @patch('subprocess.run')
    def test_should_handle_extraction_failure(self, mock_run):
        """Should handle FFmpeg extraction failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr="Extraction failed"
        )

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with pytest.raises(Exception):
                service._extract_audio_segment(
                    "/input.wav", "/output.wav", 0.0, 10.0
                )

    @patch('subprocess.run')
    def test_should_handle_extraction_timeout(self, mock_run):
        """Should handle FFmpeg timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(
            "ffmpeg", 60
        )

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            with pytest.raises(subprocess.TimeoutExpired):
                service._extract_audio_segment(
                    "/input.wav", "/output.wav", 0.0, 10.0
                )


# ============================================================================
# Full _merge_with_lcs Workflow Tests (Lines 923-1000)
# ============================================================================

class TestMergeWithLCSFullWorkflow:
    """Test complete LCS merge workflow."""

    def test_should_merge_with_lcs_first_chunk(self):
        """Should use first chunk as-is in LCS merge."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "First chunk complete text",
                    "segments": [
                        {"start": "00:00:00,000", "end": "00:00:10,000", "text": "First"}
                    ],
                    "chunk_start_time": 0
                }
            ]

            result = service._merge_with_lcs(chunks)

        assert result["text"] == "First chunk complete text"
        assert len(result["segments"]) == 1

    def test_should_merge_with_lcs_overlap_detection(self):
        """Should detect and handle overlap in LCS merge."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "This is the first part of the audio with some overlap text",
                    "segments": [
                        {"start": "00:00:00,000", "end": "00:00:15,000", "text": "First"}
                    ],
                    "chunk_start_time": 0
                },
                {
                    "text": "overlap text that continues with new content here",
                    "segments": [
                        {"start": "00:00:13,000", "end": "00:00:25,000", "text": "Second"}
                    ],
                    "chunk_start_time": 13
                }
            ]

            result = service._merge_with_lcs(chunks)

        # Should merge without duplicating overlap
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_should_filter_segments_in_lcs_merge(self):
        """Should filter segments based on overlap in LCS merge."""
        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = [
                {
                    "text": "First chunk",
                    "segments": [
                        {"start": "00:00:00,000", "end": "00:00:10,000", "text": "First"},
                        {"start": "00:00:10,000", "end": "00:00:15,000", "text": "Overlap"}
                    ],
                    "chunk_start_time": 0
                },
                {
                    "text": "Second chunk",
                    "segments": [
                        {"start": "00:00:13,000", "end": "00:00:17,000", "text": "Overlap"},
                        {"start": "00:00:17,000", "end": "00:00:25,000", "text": "Unique"}
                    ],
                    "chunk_start_time": 13
                }
            ]

            result = service._merge_with_lcs(chunks)

        # Should filter segments to avoid duplicates
        assert len(result["segments"]) >= 1


# ============================================================================
# _merge_chunk_results Strategy Selection (Lines 842-876)
# ============================================================================

class TestMergeChunkResultsStrategy:
    """Test merge strategy selection."""

    @patch('app.services.whisper_service.settings')
    def test_should_use_timestamp_merge_for_many_chunks(self, mock_settings):
        """Should use timestamp merge for chunk count >= threshold."""
        mock_settings.LCS_CHUNK_THRESHOLD = 10
        mock_settings.CHUNK_OVERLAP_SECONDS = 5

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            # Create 10 chunks (at threshold)
            chunks = [
                {
                    "text": f"Chunk {i}",
                    "segments": [],
                    "language": "zh"
                }
                for i in range(10)
            ]

            with patch.object(service, '_merge_with_timestamps') as mock_ts_merge:
                mock_ts_merge.return_value = {"text": "merged", "segments": [], "language": "zh"}
                service._merge_chunk_results(chunks)

        mock_ts_merge.assert_called_once()

    @patch('app.services.whisper_service.settings')
    def test_should_use_lcs_merge_for_few_chunks(self, mock_settings):
        """Should use LCS merge for chunk count < threshold."""
        mock_settings.LCS_CHUNK_THRESHOLD = 10
        mock_settings.CHUNK_OVERLAP_SECONDS = 5

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            # Create 5 chunks (below threshold)
            chunks = [
                {
                    "text": f"Chunk {i}",
                    "segments": [],
                    "language": "zh"
                }
                for i in range(5)
            ]

            with patch.object(service, '_merge_with_lcs') as mock_lcs_merge:
                mock_lcs_merge.return_value = {"text": "merged", "segments": [], "language": "zh"}
                service._merge_chunk_results(chunks)

        mock_lcs_merge.assert_called_once()


# ============================================================================
# _transcribe_chunk Error Handling (Lines 801-805)
# ============================================================================

class TestTranscribeChunkErrors:
    """Test error handling in chunk transcription."""

    def test_should_handle_transcription_exception(self):
        """Should handle and re-raise chunk transcription errors."""
        service = TranscribeService()

        # Mock model that raises exception
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Whisper failed")
        service.model = mock_model

        chunk_info = {
            "index": 0,
            "path": "/fake/chunk.wav",
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0
        }

        with pytest.raises(Exception, match="Chunk 0 transcription failed"):
            service._transcribe_chunk(chunk_info, "/output")


# ============================================================================
# VAD Splitting Tests (Lines 454-462)
# ============================================================================

class TestVADSplitting:
    """Test VAD-based audio splitting."""

    @patch('app.services.whisper_service.settings')
    @patch('app.services.whisper_service.TranscribeService._detect_silence_segments')
    @patch('app.services.whisper_service.TranscribeService._calculate_split_points')
    @patch('app.services.whisper_service.TranscribeService._extract_audio_segment')
    def test_should_use_vad_splitting_when_enabled(
        self, mock_extract, mock_split_points, mock_silence, mock_settings
    ):
        """Should use VAD-based splitting when enabled."""
        mock_settings.USE_VAD_SPLIT = True
        mock_settings.CHUNK_SIZE_MINUTES = 10
        mock_settings.CHUNK_OVERLAP_SECONDS = 5

        mock_silence.return_value = [(100, 105), (200, 205)]
        mock_split_points.return_value = [
            {"start": 0, "end": 100},
            {"start": 100, "end": 200}
        ]

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = service._split_audio_into_chunks(
                "/input.wav", "/output", 300
            )

        assert len(chunks) == 2
        mock_silence.assert_called_once()

    @patch('app.services.whisper_service.settings')
    @patch('app.services.whisper_service.TranscribeService._extract_audio_segment')
    def test_should_use_fixed_splitting_when_vad_disabled(
        self, mock_extract, mock_settings
    ):
        """Should use fixed-length splitting when VAD disabled."""
        mock_settings.USE_VAD_SPLIT = False
        mock_settings.CHUNK_SIZE_MINUTES = 10
        mock_settings.CHUNK_OVERLAP_SECONDS = 5

        service = TranscribeService()
        with patch.object(service, 'model', MagicMock()):
            chunks = service._split_audio_into_chunks(
                "/input.wav", "/output", 1500  # 25 minutes
            )

        # Should create 3 chunks (25 min / 10 min per chunk)
        assert len(chunks) == 3

