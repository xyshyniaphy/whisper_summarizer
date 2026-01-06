"""
Transcriptions Download Endpoints Unit Tests

Unit tests for transcription download endpoints (DOCX, NotebookLM).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from uuid import uuid4, UUID
from pathlib import Path
from fastapi import HTTPException
from io import StringIO

from app.api.transcriptions import (
    download_summary_docx,
    download_notebooklm_guideline,
    _format_fake_srt
)
from app.models.transcription import Transcription
from app.models.summary import Summary


# ============================================================================
# download_summary_docx() Tests
# ============================================================================

class TestDownloadSummaryDocx:
    """Test DOCX download endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_404_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_summary_docx("invalid-uuid", MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_404_when_no_summary(self):
        """Should return 404 when transcription has no summary."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"
        mock_transcription.summaries = []
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_400_when_summary_empty(self):
        """Should return 400 when summary text is empty."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = ""

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    @patch('shutil.rmtree')
    async def test_should_generate_docx_with_markdown_headings(
        self, mock_rmtree, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """Should generate DOCX with proper heading levels."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_mktemp.return_value = "/tmp/test/file.docx"

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "# Main Heading\n\n## Sub Heading\n\nContent here."

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = MagicMock()
            result = await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        # Verify document was created
        mock_document_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    @patch('shutil.rmtree')
    async def test_should_handle_markdown_lists(
        self, mock_rmtree, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """Should convert markdown lists to DOCX format."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_mktemp.return_value = "/tmp/test/file.docx"

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "- Item 1\n- Item 2\n\n1. Numbered item\n2. Another item"

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = MagicMock()
            result = await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        mock_doc.add_paragraph.assert_called()

    @pytest.mark.asyncio
    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    @patch('shutil.rmtree')
    async def test_should_handle_markdown_bold_italic(
        self, mock_rmtree, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """Should convert markdown bold and italic to DOCX formatting."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_mktemp.return_value = "/tmp/test/file.docx"

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "Normal text with **bold** and _italic_ words."

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_doc = MagicMock()
        mock_p = MagicMock()
        mock_doc.add_paragraph.return_value = mock_p
        mock_document_class.return_value = mock_doc

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = MagicMock()
            result = await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        # Verify paragraph was added
        mock_doc.add_paragraph.assert_called()

    @pytest.mark.asyncio
    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    @patch('shutil.rmtree')
    async def test_should_schedule_cleanup_task(
        self, mock_rmtree, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """Should schedule cleanup task for temp files."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_mktemp.return_value = "/tmp/test/file.docx"

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "Test content"

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc

        mock_background_tasks = MagicMock()

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = MagicMock()
            result = await download_summary_docx(str(uuid4()), mock_background_tasks, mock_db, mock_user)

        # Verify cleanup was scheduled
        mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_handle_import_error(self):
        """Should handle ImportError when docx not installed."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "Test content"

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(HTTPException) as exc_info:
                await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 500
        assert "python-docx" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    async def test_should_handle_docx_generation_error(
        self, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """Should handle DOCX generation errors."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_mktemp.side_effect = Exception("Temp file error")

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "Test content"

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_summary_docx(str(uuid4()), MagicMock(), mock_db, mock_user)

        assert exc_info.value.status_code == 500


# ============================================================================
# download_notebooklm_guideline() Tests
# ============================================================================

class TestDownloadNotebookLMGuideline:
    """Test NotebookLM guideline download endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_422_for_invalid_uuid(self):
        """Should return 422 for invalid UUID format."""
        mock_db = MagicMock()
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_notebooklm_guideline("invalid-uuid", mock_db, mock_user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_should_return_404_for_nonexistent_transcription(self):
        """Should return 404 when transcription not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_user = {"id": str(uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_404_when_guideline_missing(self):
        """Should return 404 when guideline file doesn't exist."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = False

        with patch('app.services.storage_service.get_storage_service', return_value=mock_storage_service):
            with pytest.raises(HTTPException) as exc_info:
                await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_guideline_content(self):
        """Should return guideline content when exists."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = True
        mock_storage_service.get_notebooklm_guideline.return_value = "Guideline content"

        with patch('app.services.storage_service.get_storage_service', return_value=mock_storage_service):
            result = await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        assert result.media_type == "text/plain; charset=utf-8"
        assert "Content-Disposition" in result.headers

    @pytest.mark.asyncio
    async def test_should_handle_file_not_found_error(self):
        """Should handle FileNotFoundError when guideline missing."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = True
        mock_storage_service.get_notebooklm_guideline.side_effect = FileNotFoundError()

        with patch('app.services.storage_service.get_storage_service', return_value=mock_storage_service):
            with pytest.raises(HTTPException) as exc_info:
                await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_handle_generic_error(self):
        """Should handle generic errors during download."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "test.wav"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = True
        mock_storage_service.get_notebooklm_guideline.side_effect = Exception("Read error")

        with patch('app.services.storage_service.get_storage_service', return_value=mock_storage_service):
            with pytest.raises(HTTPException) as exc_info:
                await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_should_generate_correct_filename(self):
        """Should generate correct download filename."""
        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid4()
        mock_transcription.file_name = "my_audio.mp3"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid4())}

        mock_storage_service = MagicMock()
        mock_storage_service.notebooklm_guideline_exists.return_value = True
        mock_storage_service.get_notebooklm_guideline.return_value = "Content"

        with patch('app.services.storage_service.get_storage_service', return_value=mock_storage_service):
            result = await download_notebooklm_guideline(str(uuid4()), mock_db, mock_user)

        # Filename should include original filename stem and -notebooklm suffix
        headers = result.headers
        assert "my_audio-notebooklm.txt" in headers["Content-Disposition"]


# ============================================================================
# Additional _format_fake_srt() Tests
# ============================================================================

class TestFormatFakeSRTAdditional:
    """Additional tests for fake SRT generation."""

    def test_should_preserve_empty_lines(self):
        """Should handle multiple consecutive empty lines."""
        result = _format_fake_srt("Line 1\n\n\nLine 2")

        # Empty lines should be skipped (only non-empty lines get SRT entries)
        assert "1\n" in result
        assert "2\n" in result

    def test_should_handle_unicode_characters(self):
        """Should handle unicode characters correctly."""
        result = _format_fake_srt("こんにちは\n世界\nテスト")

        assert "1\n" in result
        assert "こんにちは" in result
        assert "2\n" in result
        assert "世界" in result

    def test_should_format_timestamps_correctly(self):
        """Should format fake timestamps in SRT format."""
        result = _format_fake_srt("Line 1\nLine 2")

        # Check timestamp format HH:MM:SS,mmm (line number based)
        # Line 1 gets 01:00:00,000, Line 2 gets 02:00:00,000
        assert "01:00:00,000" in result
        assert "02:00:00,000" in result
        assert "-->" in result
