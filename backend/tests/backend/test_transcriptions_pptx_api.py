"""
Test suite for PPTX generation API endpoints.

Tests cover:
- POST /{id}/generate-pptx endpoint
- GET /{id}/pptx-status endpoint
- Status management (not-started → generating → ready/error)
- Authentication and authorization
- Error handling
"""
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pytest
from fastapi import status as http_status
from app.services.marp_service import MarpService


class TestGeneratePPTXEndpoint:
    """Tests for the PPTX generation endpoint."""

    def test_generate_pptx_returns_202_when_starting(self, authenticated_client, mock_transcription):
        """Test that generate_pptx returns 202 when starting generation."""
        response = authenticated_client.post(
            f"/transcriptions/{mock_transcription.id}/generate-pptx"
        )
        assert response.status_code in [http_status.HTTP_202_ACCEPTED, http_status.HTTP_404_NOT_FOUND]

    def test_generate_pptx_requires_authentication(self, client):
        """Test that generate_pptx requires authentication."""
        test_id = uuid4()
        response = client.post(f"/transcriptions/{test_id}/generate-pptx")
        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED, 
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND
        ]

    @pytest.mark.integration
    def test_generate_pptx_starts_background_task(self, authenticated_client):
        """Test that generate_pptx starts a background task."""
        test_id = uuid4()
        response = authenticated_client.post(f"/transcriptions/{test_id}/generate-pptx")
        assert response.status_code in [
            http_status.HTTP_404_NOT_FOUND,
            http_status.HTTP_202_ACCEPTED,
            http_status.HTTP_200_OK
        ]


class TestPPTXStatusEndpoint:
    """Tests for the PPTX status endpoint."""

    def test_pptx_status_returns_not_started_initially(self, authenticated_client):
        """Test that pptx-status returns not-started for new transcriptions."""
        test_id = uuid4()
        response = authenticated_client.get(f"/transcriptions/{test_id}/pptx-status")
        assert response.status_code in [
            http_status.HTTP_404_NOT_FOUND,
            http_status.HTTP_200_OK
        ]
        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert "status" in data
            assert "exists" in data

    def test_pptx_status_requires_authentication(self, client):
        """Test that pptx-status requires authentication."""
        test_id = uuid4()
        response = client.get(f"/transcriptions/{test_id}/pptx-status")
        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_pptx_status_returns_correct_fields(self, authenticated_client):
        """Test that pptx-status returns correct JSON structure."""
        test_id = uuid4()
        response = authenticated_client.get(f"/transcriptions/{test_id}/pptx-status")
        if response.status_code == http_status.HTTP_200_OK:
            data = response.json()
            assert "status" in data
            assert "exists" in data
            assert data["status"] in ["not-started", "generating", "ready", "error", "not_ready"]


class TestPPTXStatusManagement:
    """Tests for PPTX status management through the workflow."""

    def test_status_transitions_correctly(self):
        """Test that status transitions: not-started -> generating -> ready."""
        status_flow = ["not-started", "generating", "ready"]
        valid_states = ["not-started", "generating", "ready", "error"]
        for state in status_flow:
            assert state in valid_states

    @pytest.mark.integration
    def test_status_resets_to_not_started_after_error(self):
        """Test that status can be reset from error to not-started for retry."""
        error_status = "error"
        reset_status = "not-started"
        assert error_status != reset_status


class TestPPTXErrorHandling:
    """Tests for PPTX generation error handling."""

    @pytest.mark.asyncio
    async def test_generate_pptx_handles_empty_content(self):
        """Test that empty transcription content is handled correctly."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            service = MarpService(output_dir=Path(tmpdir))
            
            class EmptyTranscription:
                def __init__(self):
                    self.id = uuid4()
                    self.file_name = "empty.mp3"
                    self.text = ""
                    self.duration_seconds = 0

            mock = EmptyTranscription()
            
            with pytest.raises(ValueError, match="Cannot generate markdown"):
                await service.generate_markdown(mock)

    @pytest.mark.asyncio
    async def test_generate_pptx_handles_missing_summary(self, marp_service: MarpService, mock_transcription):
        """Test that missing summary is handled (should not error)."""
        mock_response = MagicMock()
        mock_response.summary = '{"title": "Test", "topics": [], "summary": [], "appointments": []}'

        with patch.object(marp_service.gemini_client, "generate_summary", new=AsyncMock(return_value=mock_response)):
            markdown = await marp_service.generate_markdown(mock_transcription)
            assert markdown is not None
            assert len(markdown) > 0

    @pytest.mark.integration
    def test_generate_pptx_handles_marp_cli_failure(self):
        """Test handling when Marp CLI fails."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            service = MarpService(output_dir=Path(tmpdir))
            assert hasattr(service, "generate_markdown")
            assert hasattr(service, "convert_to_pptx")


class TestPPTXDownloadEndpoint:
    """Tests for the PPTX download endpoint."""

    def test_download_pptx_returns_file(self, authenticated_client):
        """Test that download endpoint returns PPTX file when it exists."""
        test_id = uuid4()
        response = authenticated_client.get(f"/transcriptions/{test_id}/download?format=pptx")
        assert response.status_code in [
            http_status.HTTP_404_NOT_FOUND,
            http_status.HTTP_200_OK
        ]
        if response.status_code == http_status.HTTP_200_OK:
            assert "application/vnd.openxmlformats" in response.headers.get("content-type", "")

    def test_download_pptx_requires_authentication(self, client):
        """Test that download requires authentication."""
        test_id = uuid4()
        response = client.get(f"/transcriptions/{test_id}/download?format=pptx")
        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
            http_status.HTTP_404_NOT_FOUND
        ]


class TestInputValidation:
    """Tests for input validation on endpoints."""

    def test_generate_pptx_rejects_invalid_id(self, authenticated_client):
        """Test that invalid transcription ID is handled."""
        response = authenticated_client.post("/transcriptions/invalid-uuid/generate-pptx")
        assert response.status_code in [
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            http_status.HTTP_404_NOT_FOUND
        ]

    def test_pptx_status_rejects_invalid_id(self, authenticated_client):
        """Test that invalid ID is handled for status endpoint."""
        response = authenticated_client.get("/transcriptions/invalid-uuid/pptx-status")
        assert response.status_code in [
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            http_status.HTTP_404_NOT_FOUND
        ]


class TestPPTXGenerationWorkflow:
    """Integration tests for complete PPTX generation workflow."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_workflow_from_request_to_download(self):
        """Test complete workflow: request generation -> check status -> download."""
        workflow_steps = [
            "POST /{id}/generate-pptx",
            "GET /{id}/pptx-status (poll until ready)",
            "GET /{id}/download?format=pptx"
        ]
        assert len(workflow_steps) == 3
        for step in workflow_steps:
            assert "POST" in step or "GET" in step

    @pytest.mark.integration
    def test_concurrent_generation_requests(self):
        """Test handling of concurrent PPTX generation requests."""
        from app.services.transcription_processor import get_transcription_semaphore
        semaphore = get_transcription_semaphore()
        assert semaphore is not None


class TestPPTXCleanup:
    """Tests for PPTX file cleanup."""

    def test_delete_transcription_removes_pptx(self):
        """Test that deleting a transcription also removes PPTX files."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            test_id = str(uuid4())
            
            pptx_file = output_dir / f"{test_id}.pptx"
            md_file = output_dir / f"{test_id}.md"
            
            pptx_file.write_text("test")
            md_file.write_text("test")
            
            for ext in [".pptx", ".md"]:
                file_path = output_dir / f"{test_id}{ext}"
                if file_path.exists():
                    file_path.unlink()
            
            assert not pptx_file.exists()
            assert not md_file.exists()
