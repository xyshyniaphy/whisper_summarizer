"""Test AudioProcessor fixed-chunk integration"""
import pytest
from app.services.audio_processor import AudioProcessor
from unittest.mock import Mock, patch, MagicMock, call
import uuid


@pytest.fixture
def mock_processor_dependencies():
    """Mock all processor dependencies"""
    with patch('app.services.audio_processor.TranscribeService') as mock_whisper, \
         patch('app.services.audio_processor.TextFormattingService') as mock_formatting:
        yield {
            "whisper": mock_whisper,
            "formatting": mock_formatting
        }


def test_processor_uses_fixed_chunks_for_long_audio(mock_processor_dependencies):
    """Should use fixed-chunk transcription for audio >= threshold (1 hour)"""
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = True
        mock_settings.FIXED_CHUNK_THRESHOLD_MINUTES = 60
        mock_settings.FIXED_CHUNK_TARGET_DURATION = 20
        mock_settings.FIXED_CHUNK_MIN_DURATION = 10
        mock_settings.FIXED_CHUNK_MAX_DURATION = 30
        mock_settings.whisper_language = 'zh'

        processor = AudioProcessor()

        # Mock _get_audio_duration to return 2 hours (above threshold)
        with patch.object(AudioProcessor, '_get_audio_duration', return_value=7200.0):
            # Mock transcribe_fixed_chunks
            mock_whisper_instance = mock_processor_dependencies["whisper"].return_value
            mock_whisper_instance.transcribe_fixed_chunks.return_value = {
                "segments": [
                    {"start": 0.0, "end": 20.0, "text": "First 20s"},
                    {"start": 20.0, "end": 40.0, "text": "Second 20s"},
                ],
                "info": {"language": "zh"}
            }

            # Mock formatting service
            mock_formatting_instance = mock_processor_dependencies["formatting"].return_value
            mock_formatting_instance.format_transcription.return_value = {
                "formatted_text": "Formatted text",
                "summary": "Summary",
                "notebooklm_guideline": "Guideline"
            }

            # Mock file exists
            with patch('os.path.exists', return_value=True):
                result = processor.process(
                    audio_path="/fake/path/long_audio.wav",
                    language="zh"
                )

            # Should have used fixed chunks
            mock_whisper_instance.transcribe_fixed_chunks.assert_called_once()
            call_args = mock_whisper_instance.transcribe_fixed_chunks.call_args
            assert call_args[1]["target_duration_seconds"] == 20
            assert call_args[1]["min_duration_seconds"] == 10
            assert call_args[1]["max_duration_seconds"] == 30
            assert call_args[1]["language"] == "zh"

            # Check result
            assert result.text == "Formatted text"
            assert result.summary == "Summary"


def test_processor_uses_standard_transcription_for_short_audio(mock_processor_dependencies):
    """Should use standard transcription for audio < threshold"""
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = True
        mock_settings.FIXED_CHUNK_THRESHOLD_MINUTES = 60
        mock_settings.whisper_language = 'zh'

        processor = AudioProcessor()

        # Mock standard transcribe
        mock_whisper_instance = mock_processor_dependencies["whisper"].return_value
        mock_whisper_instance.transcribe.return_value = {
            "text": "Raw text",
            "segments": [{"start": 0.0, "end": 5.0, "text": "Text"}],
        }

        # Mock formatting service
        mock_formatting_instance = mock_processor_dependencies["formatting"].return_value
        mock_formatting_instance.format_transcription.return_value = {
            "formatted_text": "Formatted",
            "summary": "Summary",
            "notebooklm_guideline": "Guideline"
        }

        with patch('os.path.exists', return_value=True):
            result = processor.process(
                audio_path="/fake/path/short_audio.wav",
                language="zh"
            )

        # Should have used standard transcription
        mock_whisper_instance.transcribe.assert_called_once()
        mock_whisper_instance.transcribe_fixed_chunks.assert_not_called()

        # Check result
        assert result.text == "Formatted"
        assert result.summary == "Summary"


def test_processor_respects_enable_fixed_chunks_flag(mock_processor_dependencies):
    """Should use standard transcription when ENABLE_FIXED_CHUNKS=False"""
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = False  # Disabled
        mock_settings.whisper_language = 'zh'

        processor = AudioProcessor()

        mock_whisper_instance = mock_processor_dependencies["whisper"].return_value
        mock_whisper_instance.transcribe.return_value = {
            "text": "Raw text",
            "segments": [{"start": 0.0, "end": 5.0, "text": "Text"}],
        }

        mock_formatting_instance = mock_processor_dependencies["formatting"].return_value
        mock_formatting_instance.format_transcription.return_value = {
            "formatted_text": "Formatted",
            "summary": "Summary",
            "notebooklm_guideline": "Guideline"
        }

        with patch('os.path.exists', return_value=True):
            result = processor.process(
                audio_path="/fake/path.wav",
                language="zh"
            )

        # Should use standard transcription even for long audio
        mock_whisper_instance.transcribe.assert_called_once()
        mock_whisper_instance.transcribe_fixed_chunks.assert_not_called()


def test_process_with_timestamps_uses_fixed_chunks(mock_processor_dependencies):
    """process_with_timestamps should use fixed chunks for long audio"""
    with patch('app.services.audio_processor.settings') as mock_settings:
        mock_settings.ENABLE_FIXED_CHUNKS = True
        mock_settings.FIXED_CHUNK_THRESHOLD_MINUTES = 60
        mock_settings.FIXED_CHUNK_TARGET_DURATION = 15
        mock_settings.FIXED_CHUNK_MIN_DURATION = 10
        mock_settings.FIXED_CHUNK_MAX_DURATION = 25
        mock_settings.whisper_language = 'zh'

        processor = AudioProcessor()

        # Mock _get_audio_duration to return 2 hours (above threshold)
        with patch.object(AudioProcessor, '_get_audio_duration', return_value=7200.0):
            # Mock transcribe_fixed_chunks
            mock_whisper_instance = mock_processor_dependencies["whisper"].return_value
            mock_whisper_instance.transcribe_fixed_chunks.return_value = {
                "segments": [
                    {"start": 0.0, "end": 15.0, "text": "Chunk 1"},
                    {"start": 15.0, "end": 30.0, "text": "Chunk 2"},
                ],
                "info": {"language": "zh"}
            }

            # Mock formatting service
            mock_formatting_instance = mock_processor_dependencies["formatting"].return_value
            mock_formatting_instance.format_transcription.return_value = {
                "formatted_text": "Formatted text",
                "summary": "Summary",
            }

            result = processor.process_with_timestamps(
                audio_path="/fake/path/long_audio.wav",
                language="zh"
            )

            # Should have used fixed chunks
            mock_whisper_instance.transcribe_fixed_chunks.assert_called_once()
            call_args = mock_whisper_instance.transcribe_fixed_chunks.call_args
            assert call_args[1]["target_duration_seconds"] == 15
            assert call_args[1]["min_duration_seconds"] == 10
            assert call_args[1]["max_duration_seconds"] == 25

            # Check result includes segments
            assert "segments" in result
            assert result["segments"] == [
                {"start": 0.0, "end": 15.0, "text": "Chunk 1"},
                {"start": 15.0, "end": 30.0, "text": "Chunk 2"},
            ]
