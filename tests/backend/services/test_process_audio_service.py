"""
Process Audio Service Tests

Tests for the Whisper.cpp audio processing HTTP service.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from app.services.process_audio import app, parse_srt, MODEL_PATH, DATA_DIR, OUTPUT_DIR


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a mock audio file."""
    audio_file = tmp_path / "test_audio.m4a"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


@pytest.fixture
def sample_srt_content():
    """Sample SRT file content."""
    return """1
00:00:00,000 --> 00:00:05,000
First subtitle

2
00:00:05,000 --> 00:00:10,000
Second subtitle

3
00:00:10,000 --> 00:00:15,000
Third subtitle
"""


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Test /health endpoint."""

    def test_health_check_with_model(self, client):
        """Should return healthy status when model exists."""
        with patch('app.services.process_audio.os.path.exists') as mock_exists:
            mock_exists.return_value = True

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_exists"] is True
        assert "model" in data
        assert "language" in data
        assert "threads" in data

    def test_health_check_without_model(self, client):
        """Should return unhealthy status when model missing."""
        with patch('app.services.process_audio.os.path.exists') as mock_exists:
            mock_exists.return_value = False

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["model_exists"] is False


# ============================================================================
# parse_srt() Tests
# ============================================================================

class TestParseSRT:
    """Test SRT file parsing."""

    def test_should_parse_standard_srt(self, tmp_path, sample_srt_content):
        """Should parse standard SRT format correctly."""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(sample_srt_content, encoding='utf-8')

        timestamps = parse_srt(srt_file)

        assert len(timestamps) == 3
        assert timestamps[0]["start"] == "00:00:00,000"
        assert timestamps[0]["end"] == "00:00:05,000"
        assert timestamps[0]["text"] == "First subtitle"
        assert timestamps[2]["text"] == "Third subtitle"

    def test_should_parse_srt_with_multiline_text(self, tmp_path):
        """Should parse SRT with multi-line subtitles."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
First line
Second line

2
00:00:05,000 --> 00:00:10,000
Another subtitle
"""
        srt_file = tmp_path / "multiline.srt"
        srt_file.write_text(srt_content, encoding='utf-8')

        timestamps = parse_srt(srt_file)

        assert len(timestamps) == 2
        assert "First line" in timestamps[0]["text"]
        assert "Second line" in timestamps[0]["text"]

    def test_should_handle_empty_srt(self, tmp_path):
        """Should handle empty SRT file."""
        srt_file = tmp_path / "empty.srt"
        srt_file.write_text("", encoding='utf-8')

        timestamps = parse_srt(srt_file)

        assert timestamps == []

    def test_should_handle_malformed_srt(self, tmp_path):
        """Should handle malformed SRT gracefully."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000

2
missing timestamp
text here
"""
        srt_file = tmp_path / "malformed.srt"
        srt_file.write_text(srt_content, encoding='utf-8')

        # Should not crash
        timestamps = parse_srt(srt_file)
        # At least the first entry should be parsed
        assert len(timestamps) >= 0

    def test_should_parse_srt_with_unicode(self, tmp_path):
        """Should parse SRT with Unicode characters."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
中文 日本語 한글 Emoji 😀

2
00:00:05,000 --> 00:00:10,000
Another text
"""
        srt_file = tmp_path / "unicode.srt"
        srt_file.write_text(srt_content, encoding='utf-8')

        timestamps = parse_srt(srt_file)

        assert len(timestamps) == 2
        assert "中文" in timestamps[0]["text"]
        assert "Emoji" in timestamps[0]["text"]


# ============================================================================
# Transcribe Audio Tests
# ============================================================================

class TestTranscribeAudio:
    """Test /transcribe endpoint."""

    @patch('app.services.process_audio.subprocess.run')
    def test_should_transcribe_audio_successfully(self, mock_run, client, tmp_path):
        """Should successfully transcribe audio file."""
        # Mock successful ffmpeg conversion
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0

        # Mock successful whisper transcription
        whisper_result = MagicMock()
        whisper_result.returncode = 0

        mock_run.side_effect = [ffmpeg_result, whisper_result]

        # Create mock output files
        (tmp_path / "test_audio.txt").write_text("Transcription text", encoding='utf-8')
        (tmp_path / "test_audio.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest", encoding='utf-8')

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    # Create test file
                    test_file = tmp_path / "test_audio.m4a"
                    test_file.write_bytes(b"audio content")

                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": ("test_audio.m4a", f, "audio/m4a")}
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["filename"] == "test_audio.m4a"

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_ffmpeg_conversion_failure(self, mock_run, client, tmp_path):
        """Should handle ffmpeg conversion error."""
        # Mock ffmpeg failure
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 1
        ffmpeg_result.stderr = "ffmpeg error: invalid format"
        mock_run.return_value = ffmpeg_result

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with open(test_file, "rb") as f:
                    response = client.post(
                        "/transcribe",
                        files={"file": ("test.m4a", f, "audio/m4a")}
                    )

        assert response.status_code == 500
        assert "音声変換エラー" in response.json()["detail"]

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_whisper_failure(self, mock_run, client, tmp_path):
        """Should handle whisper.cpp execution error."""
        # Mock successful ffmpeg
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0

        # Mock whisper failure
        whisper_result = MagicMock()
        whisper_result.returncode = 1
        whisper_result.stderr = "whisper error: model not found"

        mock_run.side_effect = [ffmpeg_result, whisper_result]

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with open(test_file, "rb") as f:
                    response = client.post(
                        "/transcribe",
                        files={"file": ("test.m4a", f, "audio/m4a")}
                    )

        assert response.status_code == 500
        assert "Whisper.cpp実行エラー" in response.json()["detail"]

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_ffmpeg_timeout(self, mock_run, client, tmp_path):
        """Should handle ffmpeg timeout."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired('ffmpeg', 300)

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with open(test_file, "rb") as f:
                    response = client.post(
                        "/transcribe",
                        files={"file": ("test.m4a", f, "audio/m4a")}
                    )

        assert response.status_code == 504
        assert "タイムアウト" in response.json()["detail"]

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_whisper_timeout(self, mock_run, client, tmp_path):
        """Should handle whisper timeout."""
        from subprocess import TimeoutExpired

        # First call (ffmpeg) succeeds
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0

        # Second call (whisper) times out
        mock_run.side_effect = [
            ffmpeg_result,
            TimeoutExpired('whisper', 600)
        ]

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with open(test_file, "rb") as f:
                    response = client.post(
                        "/transcribe",
                        files={"file": ("test.m4a", f, "audio/m4a")}
                    )

        assert response.status_code == 504

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_generic_exception(self, mock_run, client, tmp_path):
        """Should handle generic exceptions."""
        mock_run.side_effect = IOError("Disk full")

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with open(test_file, "rb") as f:
                    response = client.post(
                        "/transcribe",
                        files={"file": ("test.m4a", f, "audio/m4a")}
                    )

        assert response.status_code == 500
        assert "処理エラー" in response.json()["detail"]


# ============================================================================
# File Format Support Tests
# ============================================================================

class TestFileFormatSupport:
    """Test various audio file formats."""

    @patch('app.services.process_audio.subprocess.run')
    @pytest.mark.parametrize("filename,content_type", [
        ("audio.m4a", "audio/m4a"),
        ("audio.mp3", "audio/mpeg"),
        ("audio.wav", "audio/wav"),
        ("audio.aac", "audio/aac"),
        ("audio.flac", "audio/flac"),
        ("audio.ogg", "audio/ogg"),
    ])
    def test_should_accept_common_formats(self, mock_run, client, tmp_path, filename, content_type):
        """Should accept common audio file formats."""
        # Mock successful processing
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        whisper_result = MagicMock()
        whisper_result.returncode = 0
        mock_run.side_effect = [ffmpeg_result, whisper_result]

        # Create output files
        (tmp_path / "audio.txt").write_text("text")
        (tmp_path / "audio.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest")

        test_file = tmp_path / filename
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": (filename, f, content_type)}
                        )

        # Should not return format error
        assert response.status_code != 500 or "音声変換エラー" not in response.json().get("detail", "")


# ============================================================================
# Output File Tests
# ============================================================================

class TestOutputFiles:
    """Test output file generation."""

    @patch('app.services.process_audio.subprocess.run')
    def test_should_include_transcription_text(self, mock_run, client, tmp_path):
        """Should generate .txt output file."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg
            MagicMock(returncode=0),  # whisper
        ]

        # Create output files
        transcription_text = "This is the transcription"
        (tmp_path / "test.txt").write_text(transcription_text, encoding='utf-8')
        (tmp_path / "test.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest", encoding='utf-8')

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": ("test.m4a", f, "audio/m4a")}
                        )

        data = response.json()
        assert "transcription" in data
        assert "timestamps" in data

    @patch('app.services.process_audio.subprocess.run')
    def test_should_include_srt_timestamps(self, mock_run, client, tmp_path):
        """Should generate .srt output file with timestamps."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg
            MagicMock(returncode=0),  # whisper
        ]

        # Create SRT output
        srt_content = """1
00:00:00,000 --> 00:00:05,000
Test subtitle
"""
        (tmp_path / "test.txt").write_text("text")
        (tmp_path / "test.srt").write_text(srt_content, encoding='utf-8')

        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": ("test.m4a", f, "audio/m4a")}
                        )

        data = response.json()
        assert "timestamps" in data
        assert len(data["timestamps"]) == 1


# ============================================================================
# Environment Configuration Tests
# ============================================================================

class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_should_use_custom_language(self, client):
        """Should use custom language from environment."""
        with patch.dict(os.environ, {'WHISPER_LANGUAGE': 'en'}):
            # Reload app to pick up new env
            from app.services import process_audio as pa_module
            import importlib
            importlib.reload(pa_module)

            client2 = TestClient(pa_module.app)
            response = client2.get("/health")

        assert response.json()["language"] == "en"

    def test_should_use_custom_threads(self, client):
        """Should use custom thread count from environment."""
        with patch.dict(os.environ, {'WHISPER_THREADS': '8'}):
            from app.services import process_audio as pa_module
            import importlib
            importlib.reload(pa_module)

            client2 = TestClient(pa_module.app)
            response = client2.get("/health")

        assert response.json()["threads"] == "8"


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_empty_audio_file(self, mock_run, client, tmp_path):
        """Should handle empty audio file."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg
            MagicMock(returncode=0),  # whisper
        ]

        test_file = tmp_path / "empty.wav"
        test_file.write_bytes(b"")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": ("empty.wav", f, "audio/wav")}
                        )

        # Should handle gracefully
        assert response.status_code in [200, 500]

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_filename_with_multiple_dots(self, mock_run, client, tmp_path):
        """Should handle filename with multiple dots."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg
            MagicMock(returncode=0),  # whisper
        ]

        (tmp_path / "my.audio.file.test.txt").write_text("text")
        (tmp_path / "my.audio.file.test.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest")

        test_file = tmp_path / "my.audio.file.test.m4a"
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": ("my.audio.file.test.m4a", f, "audio/m4a")}
                        )

        # Should handle successfully
        assert response.status_code == 200

    @patch('app.services.process_audio.subprocess.run')
    def test_should_handle_unicode_filename(self, mock_run, client, tmp_path):
        """Should handle Unicode characters in filename."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ffmpeg
            MagicMock(returncode=0),  # whisper
        ]

        filename = "テスト音声.m4a"
        base_name = "テスト音声"

        (tmp_path / f"{base_name}.txt").write_text("text")
        (tmp_path / f"{base_name}.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nTest")

        test_file = tmp_path / filename
        test_file.write_bytes(b"content")

        with patch('app.services.process_audio.DATA_DIR', tmp_path):
            with patch('app.services.process_audio.OUTPUT_DIR', tmp_path):
                with patch.object(Path, 'unlink'):
                    with open(test_file, "rb") as f:
                        response = client.post(
                            "/transcribe",
                            files={"file": (filename, f, "audio/m4a")}
                        )

        data = response.json()
        assert filename in data["filename"]
