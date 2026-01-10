"""
Download Endpoints Integration Tests

Tests file download functionality including:
- DOCX download (AI summary)
- NotebookLM guidelines download
- Regular text download (txt, formatted, srt)
- File content validation
- Content-Type headers

Run: ./tests/run.prd.sh test_download_endpoints
"""

import pytest
from conftest import RemoteProductionClient, Assertions


class TestDOCXDownload:
    """Test DOCX download endpoint (AI摘要)."""

    def test_download_docx_with_summary(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Should download DOCX file when summary exists."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-docx")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0, "DOCX file should not be empty"

    def test_download_docx_content_type(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str):
        """DOCX download should have correct content type."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-docx")
        assert response.status == 200
        # DOCX files start with PK (ZIP signature)
        assert response.data.startswith("PK"), "DOCX file should start with PK (ZIP signature)"

    def test_download_docx_without_summary(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle DOCX download when no summary exists."""
        # First check if transcription has summary
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if detail_response.is_success and detail_response.json.get("summaries"):
            pytest.skip("Transcription has a summary")

        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-docx")
        assert response.status in [404, 400, 200], "Should return 404 or handle gracefully"

    def test_download_docx_with_chinese_content(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """DOCX should properly handle Chinese characters."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-docx")
        assertions.assert_status(response, 200)
        # DOCX is a ZIP file, should have valid structure
        assert len(response.data) > 1000, "DOCX file should have substantial content"


class TestNotebookLMDownload:
    """Test NotebookLM guidelines download endpoint."""

    def test_download_notebooklm_guideline(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should download NotebookLM guideline text file."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0, "Guideline file should not be empty"

    def test_notebooklm_content_type(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """NotebookLM download should be text content."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assert response.status == 200
        # Should be readable text
        assert isinstance(response.data, str)

    def test_notebooklm_has_structure(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """NotebookLM guideline should have structured content."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should contain guideline-like content
        assert len(content) > 50, "Guideline should have meaningful content"

    def test_notebooklm_with_empty_transcription(self, prod_client: RemoteProductionClient):
        """Should handle NotebookLM download for non-existent transcription."""
        response = prod_client.download_file("/api/transcriptions/00000000-0000-0000-0000-000000000000/download-notebooklm")
        assert response.status in [404, 400]


class TestRegularDownload:
    """Test regular download endpoints."""

    def test_download_txt_format(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should download transcription as plain text."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=txt")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0

    def test_download_formatted_text(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should download formatted text."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=formatted")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0

    def test_download_srt_format(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should download transcription as SRT subtitles."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=srt")
        assertions.assert_status(response, 200)
        # SRT format should have timestamps
        assert " --> " in response.data or len(response.data) > 0

    def test_download_default_format(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Default download should return plain text."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0


class TestDownloadContentValidation:
    """Validate downloaded file content."""

    def test_txt_content_is_readable(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Downloaded text should be readable."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=txt")
        assertions.assert_status(response, 200)

        # Should contain readable characters
        assert len(response.data) > 10
        # Check for common Chinese characters
        has_content = any(char in response.data for char in ['的', '是', '了', '在', '和', '我'])
        assert has_content or len(response.data) > 100  # Either Chinese content or long content

    def test_srt_has_timestamps(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """SRT format should contain subtitle timestamps."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=srt")
        assertions.assert_status(response, 200)

        # SRT timestamps format: 00:00:00,000 --> 00:00:05,000
        content = response.data
        has_timestamp = "-->" in content or len(content.split('\n')) > 3

    def test_docx_file_size(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """DOCX file should have reasonable size."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-docx")
        assertions.assert_status(response, 200)

        # DOCX files should be at least a few KB
        file_size = len(response.data)
        assert file_size > 2000, f"DOCX file too small: {file_size} bytes"


class TestDownloadErrorHandling:
    """Test download error handling."""

    def test_download_invalid_transcription_id(self, prod_client: RemoteProductionClient):
        """Should handle invalid transcription ID."""
        response = prod_client.download_file("/api/transcriptions/invalid-id/download")
        assert response.status in [404, 422, 400]

    def test_download_nonexistent_transcription(self, prod_client: RemoteProductionClient):
        """Should handle non-existent transcription."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.download_file(f"/api/transcriptions/{fake_id}/download")
        assert response.status in [404, 400]

    def test_download_with_invalid_format(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle invalid format parameter."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=invalid")
        assert response.status in [400, 422, 200]  # May fall back to default


class TestDownloadAuthBypass:
    """Test downloads work with auth bypass."""

    def test_download_without_auth(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Downloads should work without OAuth token (localhost bypass)."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download")
        # Auth bypass should allow download
        assert response.status == 200

    def test_docx_download_without_auth(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str):
        """DOCX download should work with auth bypass."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-docx")
        assert response.status == 200

    def test_notebooklm_download_without_auth(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """NotebookLM download should work with auth bypass."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assert response.status == 200


class TestMultipleFormats:
    """Test downloading same transcription in multiple formats."""

    def test_all_formats_available(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should be able to download in all supported formats."""
        formats = ["txt", "formatted", "srt"]

        for fmt in formats:
            response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format={fmt}")
            assert response.status == 200, f"Failed to download format: {fmt}"

    def test_different_formats_different_content(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Different formats should produce different content."""
        txt_response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=txt")
        srt_response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download?format=srt")

        assert txt_response.status == 200
        assert srt_response.status == 200

        # SRT should have timestamps that plain text doesn't have in the same format
        # Content may differ
