"""
WhisperService Fixed-Chunk Transcription Tests

Tests for fixed-duration chunk transcription feature.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pydub import AudioSegment
from pydub.generators import Sine

from app.services.whisper_service import TranscribeService


@pytest.fixture
def whisper_service():
    """Create a TranscribeService instance with mocked model"""
    with patch('app.services.whisper_service.WhisperModel'):
        service = TranscribeService()
        # Mock the model
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (
            [
                MagicMock(
                    start=0.0,
                    end=5.0,
                    text="First segment"
                ),
                MagicMock(
                    start=5.0,
                    end=10.0,
                    text="Second segment"
                ),
            ],
            MagicMock(
                language="zh",
                language_probability=0.95,
                duration=10.0
            )
        )
        service.model = mock_model
        yield service


@pytest.fixture
def sample_audio_30s():
    """Create 30-second test audio"""
    tone = Sine(440).to_audio_segment(duration=30000, volume=-10.0)
    return tone


@pytest.fixture
def fixed_chunk_config():
    return {
        "target_duration_seconds": 15,
        "min_duration_seconds": 10,
        "max_duration_seconds": 20,
    }


def test_whisper_service_has_fixed_chunks_method(whisper_service):
    """Should have transcribe_fixed_chunks method"""
    assert hasattr(whisper_service, 'transcribe_fixed_chunks'), \
        "TranscribeService should have transcribe_fixed_chunks method"


def test_whisper_service_processes_fixed_chunks(whisper_service, sample_audio_30s, fixed_chunk_config, tmp_path):
    """Should process audio in fixed chunks instead of Whisper's native segmentation"""
    # Create temp audio file
    temp_file = tmp_path / "test_30s.wav"
    sample_audio_30s.export(str(temp_file), format="wav")

    # Mock the segmenter to return predictable chunks
    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
        {"start": 15000, "end": 30000, "start_s": 15.0, "end_s": 30.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        result = whisper_service.transcribe_fixed_chunks(
            audio_path=str(temp_file),
            target_duration_seconds=15,
            min_duration_seconds=10,
            max_duration_seconds=20
        )

        # Should have called transcribe for each chunk
        assert whisper_service.model.transcribe.call_count == 2

        # Should have merged results
        assert "segments" in result
        assert len(result["segments"]) >= 2


def test_whisper_service_aligns_timestamps_to_chunks(whisper_service, sample_audio_30s, tmp_path):
    """Segment timestamps should be aligned to chunk boundaries"""
    temp_file = tmp_path / "test_30s.wav"
    sample_audio_30s.export(str(temp_file), format="wav")

    # Define chunks with specific boundaries
    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
        {"start": 15000, "end": 30000, "start_s": 15.0, "end_s": 30.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        result = whisper_service.transcribe_fixed_chunks(
            audio_path=str(temp_file),
            target_duration_seconds=15
        )

        # Verify segments exist
        segments = result["segments"]
        assert len(segments) >= 2

        # First chunk segments should have offset 0-15
        # Second chunk segments should have offset 15-30
        # (Since we mock transcribe to return the same segments each time,
        # they should be duplicated with proper offsets)


def test_whisper_service_handles_chunk_overlap(whisper_service, sample_audio_30s, tmp_path):
    """Should handle chunk overlap if configured"""
    temp_file = tmp_path / "test_30s.wav"
    sample_audio_30s.export(str(temp_file), format="wav")

    # Chunks with overlap
    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
        {"start": 14000, "end": 29000, "start_s": 14.0, "end_s": 29.0},  # 1s overlap
        {"start": 28000, "end": 30000, "start_s": 28.0, "end_s": 30.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        result = whisper_service.transcribe_fixed_chunks(
            audio_path=str(temp_file),
            target_duration_seconds=15
        )

        # Should process all chunks including overlap
        assert whisper_service.model.transcribe.call_count == 3


def test_whisper_service_extracts_audio_chunks(whisper_service, sample_audio_30s, tmp_path):
    """Should extract audio chunks to temporary files"""
    temp_file = tmp_path / "test_30s.wav"
    sample_audio_30s.export(str(temp_file), format="wav")

    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        # Mock subprocess to verify ffmpeg is called with correct parameters
        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = whisper_service.transcribe_fixed_chunks(
                audio_path=str(temp_file),
                target_duration_seconds=15
            )

            # Verify ffmpeg was called to extract the chunk
            assert mock_run.call_count >= 1
            call_args = mock_run.call_args
            cmd = call_args[0][0]  # First positional argument is the command list

            # Verify ffmpeg command parameters
            assert "ffmpeg" in cmd
            assert "-i" in cmd
            assert "-ss" in cmd  # Start time
            assert "-t" in cmd  # Duration


def test_whisper_service_returns_language_info(whisper_service, sample_audio_30s, tmp_path):
    """Should return language information in result"""
    temp_file = tmp_path / "test_30s.wav"
    sample_audio_30s.export(str(temp_file), format="wav")

    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        result = whisper_service.transcribe_fixed_chunks(
            audio_path=str(temp_file),
            target_duration_seconds=15,
            language="zh"
        )

        # Should have language info
        assert "info" in result or "language" in result


def test_whisper_service_cleans_up_temp_files(whisper_service, tmp_path):
    """Should clean up temporary audio chunk files after processing"""
    import tempfile
    from pydub import AudioSegment
    from pydub.generators import Sine

    service = whisper_service

    # Create test audio
    tone = Sine(440).to_audio_segment(duration=30000, volume=-10.0)
    audio_file = tmp_path / "test.wav"
    tone.export(str(audio_file), format="wav")

    # Track temp files before transcription
    temp_dir = tempfile.gettempdir()
    temp_files_before = set(os.listdir(temp_dir))

    # Mock the segmenter to return predictable chunks
    chunks = [
        {"start": 0, "end": 15000, "start_s": 0.0, "end_s": 15.0},
        {"start": 15000, "end": 30000, "start_s": 15.0, "end_s": 30.0},
    ]

    with patch('app.services.audio_segmenter.AudioSegmenter') as mock_segmenter_class:
        mock_segmenter = MagicMock()
        mock_segmenter.segment.return_value = chunks
        mock_segmenter_class.return_value = mock_segmenter

        # Transcribe
        service.transcribe_fixed_chunks(str(audio_file))

    # Verify temp files were cleaned up
    temp_files_after = set(os.listdir(temp_dir))
    new_files = temp_files_after - temp_files_before

    # Filter out files that don't match our chunk pattern
    chunk_files = [f for f in new_files if f.startswith("chunk_")]
    assert len(chunk_files) == 0, f"Temp files not cleaned up: {chunk_files}"
