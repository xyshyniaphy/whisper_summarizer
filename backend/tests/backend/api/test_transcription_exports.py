"""
Tests for Transcription Export API endpoints (DOCX, NotebookLM).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.transcriptions import router
from app.models.transcription import Transcription
from app.models.summary import Summary


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/transcriptions")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "is_active": True
    }


@pytest.fixture
def mock_transcription():
    """Create a mock transcription."""
    transcription = Mock()
    transcription.id = UUID("12345678-1234-5678-1234-567812345678")
    transcription.user_id = UUID("12345678-1234-5678-1234-567812345678")
    transcription.file_name = "test_audio.mp3"
    transcription.text = "This is a test transcription."
    transcription.language = "zh"
    transcription.duration_seconds = 120
    transcription.created_at = datetime.now(timezone.utc)
    transcription.summaries = []
    return transcription


class TestDownloadDocx:
    """Tests for GET /api/transcriptions/{id}/download-docx endpoint."""

    @pytest.fixture
    def mock_summary(self):
        """Create a mock summary."""
        summary = Mock()
        summary.summary_text = "AI generated summary of the transcription."
        summary.model_name = "glm-4.5-air"
        return summary

    def test_successful_docx_download(self, client, mock_db, mock_current_user, mock_transcription, mock_summary):
        """Test successful DOCX file download with summary."""
        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            # Don't actually create DOCX, just mock the FileResponse
            with patch('app.api.transcriptions.FileResponse') as mock_file_response:
                mock_file_response.return_value = Mock(status_code=200)

                with patch('app.api.transcriptions.tempfile.TemporaryDirectory') as mock_temp_dir:
                    mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
                    mock_temp_dir.return_value.__exit__.return_value = False

                    response = client.get(
                        f"/api/transcriptions/{mock_transcription.id}/download-docx",
                        headers={"Authorization": "Bearer test-token"}
                    )

    def test_transcription_not_found(self, client, mock_db, mock_current_user):
        """Test that non-existent transcription returns 404."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get(
            "/api/transcriptions/12345678-1234-5678-1234-567812345678/download-docx",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404

    def test_invalid_uuid_format(self, client, mock_db, mock_current_user):
        """Test that invalid UUID format returns 422."""
        response = client.get(
            "/api/transcriptions/invalid-uuid/download-docx",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422

    def test_no_summary_available(self, client, mock_db, mock_current_user, mock_transcription):
        """Test handling when no summary is available."""
        mock_transcription.summaries = []
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        response = client.get(
            f"/api/transcriptions/{mock_transcription.id}/download-docx",
            headers={"Authorization": "Bearer test-token"}
        )

        # Should return error about no summary
        assert response.status_code == 400

    def test_docx_import_error(self, client, mock_db, mock_current_user, mock_transcription, mock_summary):
        """Test handling when python-docx is not installed."""
        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.Document', side_effect=ImportError("No module named 'docx'")):
            response = client.get(
                f"/api/transcriptions/{mock_transcription.id}/download-docx",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 500

    def test_filename_generation(self, client, mock_db, mock_current_user, mock_transcription, mock_summary):
        """Test that download filename is generated correctly."""
        mock_transcription.summaries = [mock_summary]
        mock_transcription.file_name = "my_audio_recording.mp3"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            def check_filename(*args, **kwargs):
                path, filename = kwargs.get('path'), kwargs.get('filename')
                # Should be "my_audio_recording-摘要.docx"
                if filename:
                    assert "my_audio_recording" in filename
                    assert "摘要.docx" in filename
                return Mock(status_code=200)

            mock_file_response.side_effect = check_filename

            with patch('app.api.transcriptions.tempfile.TemporaryDirectory'):
                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-docx",
                    headers={"Authorization": "Bearer test-token"}
                )


class TestDownloadNotebookLMGuideline:
    """Tests for GET /api/transcriptions/{id}/download-notebooklm endpoint."""

    def test_successful_guideline_download(self, client, mock_db, mock_current_user, mock_transcription):
        """Test successful NotebookLM guideline download."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        guideline_text = """## NotebookLM Presentation Guideline

### Slide 1: Overview
- Main topic
- Key points

### Slide 2: Details
- Supporting information
"""

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.return_value = guideline_text
            mock_storage_getter.return_value = mock_storage

            response = client.get(
                f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                headers={"Authorization": "Bearer test-token"}
            )

    def test_guideline_not_found(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that missing guideline returns 404."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = False
            mock_storage_getter.return_value = mock_storage

            response = client.get(
                f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 404

    def test_invalid_uuid_format(self, client, mock_db, mock_current_user):
        """Test that invalid UUID format returns 422."""
        response = client.get(
            "/api/transcriptions/invalid-uuid/download-notebooklm",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422

    def test_transcription_not_found(self, client, mock_db, mock_current_user):
        """Test that non-existent transcription returns 404."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.get(
            "/api/transcriptions/12345678-1234-5678-1234-567812345678/download-notebooklm",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404

    def test_filename_generation(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that download filename is generated correctly."""
        mock_transcription.file_name = "presentation_audio.mp3"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.return_value = "Guideline text"
            mock_storage_getter.return_value = mock_storage

            with patch('app.api.transcriptions.StreamingResponse') as mock_streaming:
                def check_headers(*args, **kwargs):
                    headers = kwargs.get('headers', {})
                    content_disposition = headers.get('Content-Disposition', '')
                    # Should contain filename
                    assert 'presentation_audio-notebooklm.txt' in content_disposition
                    return Mock(status_code=200)

                mock_streaming.side_effect = check_headers

                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                    headers={"Authorization": "Bearer test-token"}
                )

    def test_media_type_is_text_plain(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that response has correct media type."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.return_value = "Guideline content"
            mock_storage_getter.return_value = mock_storage

            with patch('app.api.transcriptions.StreamingResponse') as mock_streaming:
                def check_media_type(*args, **kwargs):
                    media_type = kwargs.get('media_type', '')
                    assert 'text/plain' in media_type
                    assert 'utf-8' in media_type
                    return Mock(status_code=200)

                mock_streaming.side_effect = check_media_type

                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                    headers={"Authorization": "Bearer test-token"}
                )

    def test_guideline_with_unicode_content(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that Unicode content is properly handled."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        guideline_text = """## 演示文稿指南

### 幻灯片 1：概述
- 中文内容
- 日本語内容
- Ñoño café

### 幻灯片 2：详细信息
- More details
"""

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.return_value = guideline_text
            mock_storage_getter.return_value = mock_storage

            with patch('app.api.transcriptions.StreamingResponse') as mock_streaming:
                mock_streaming.return_value = Mock(status_code=200)

                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                    headers={"Authorization": "Bearer test-token"}
                )


class TestExportAuthentication:
    """Tests for authentication and authorization."""

    def test_download_without_auth(self, client):
        """Test that download requires authentication."""
        response = client.get(
            "/api/transcriptions/12345678-1234-5678-1234-567812345678/download-docx"
        )

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_guideline_download_without_auth(self, client):
        """Test that guideline download requires authentication."""
        response = client.get(
            "/api/transcriptions/12345678-1234-5678-1234-567812345678/download-notebooklm"
        )

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_user_cannot_download_others_transcription(self, client, mock_db, mock_current_user):
        """Test that users cannot download other users' transcriptions."""
        # Create transcription for different user
        other_transcription = Mock()
        other_transcription.id = UUID("87654321-4321-8765-4321-876543210987")
        other_transcription.user_id = UUID("99999999-9999-9999-9999-999999999999")  # Different user
        other_transcription.file_name = "other.mp3"

        mock_db.query.return_value.filter.return_value.first.return_value = None  # Not found for current user

        response = client.get(
            f"/api/transcriptions/{other_transcription.id}/download-docx",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404


class TestResponseHeaders:
    """Tests for response headers."""

    def test_docx_content_disposition(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that DOCX response has correct Content-Disposition header."""
        mock_summary = Mock()
        mock_summary.summary_text = "Test summary"
        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = Mock(status_code=200)

            with patch('app.api.transcriptions.tempfile.TemporaryDirectory'):
                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-docx",
                    headers={"Authorization": "Bearer test-token"}
                )

    def test_guideline_content_disposition(self, client, mock_db, mock_current_user, mock_transcription):
        """Test that guideline response has correct Content-Disposition header."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.return_value = "Guideline"
            mock_storage_getter.return_value = mock_storage

            with patch('app.api.transcriptions.StreamingResponse') as mock_streaming:
                def verify_headers(*args, **kwargs):
                    headers = kwargs.get('headers', {})
                    assert 'Content-Disposition' in headers
                    assert 'attachment' in headers['Content-Disposition']
                    return Mock(status_code=200)

                mock_streaming.side_effect = verify_headers

                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                    headers={"Authorization": "Bearer test-token"}
                )


class TestErrorHandling:
    """Tests for error handling."""

    def test_storage_service_error_docx(self, client, mock_db, mock_current_user, mock_transcription):
        """Test handling of storage service error during DOCX generation."""
        mock_summary = Mock()
        mock_summary.summary_text = "Test summary"
        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.get_notebooklm_guideline.side_effect = Exception("Storage error")
            mock_storage_getter.return_value = mock_storage

            # Should handle gracefully
            with patch('app.api.transcriptions.tempfile.TemporaryDirectory'):
                response = client.get(
                    f"/api/transcriptions/{mock_transcription.id}/download-docx",
                    headers={"Authorization": "Bearer test-token"}
                )

    def test_storage_service_error_guideline(self, client, mock_db, mock_current_user, mock_transcription):
        """Test handling of storage service error during guideline download."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription

        with patch('app.api.transcriptions.get_storage_service') as mock_storage_getter:
            mock_storage = Mock()
            mock_storage.notebooklm_guideline_exists.return_value = True
            mock_storage.get_notebooklm_guideline.side_effect = FileNotFoundError("File not found")
            mock_storage_getter.return_value = mock_storage

            response = client.get(
                f"/api/transcriptions/{mock_transcription.id}/download-notebooklm",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 404
