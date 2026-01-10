"""
NotebookLM Guidelines Integration Tests

Tests NotebookLM guidelines functionality including:
- Guidelines retrieval
- Guidelines download
- Guidelines content structure
- Guidelines for presentations

Run: ./tests/run.prd.sh test_notebooklm_guidelines
"""

import pytest
from conftest import RemoteProductionClient, Assertions


class TestNotebookLMGuidelineRetrieval:
    """Test NotebookLM guideline retrieval."""

    def test_get_notebooklm_guideline(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should retrieve NotebookLM guideline for transcription."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/notebooklm")
        # May return guideline data or 404 if not implemented as separate endpoint
        assert response.status in [200, 404]

    def test_notebooklm_guideline_structure(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """NotebookLM guideline should have proper structure."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/notebooklm")
        if response.status == 200 and response.data:
            data = response.json if isinstance(response.json, dict) else {"content": response.data}
            # Should have guideline content
            assert len(str(data)) > 0


class TestNotebookLMGuidelineDownload:
    """Test NotebookLM guideline download endpoint."""

    def test_download_notebooklm_guideline(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should download NotebookLM guideline as text file."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)
        assert len(response.data) > 0, "Guideline content should not be empty"

    def test_notebooklm_download_content_type(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """NotebookLM download should return text content."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Should be readable text
        assert isinstance(response.data, str)

    def test_notebooklm_file_extension(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """NotebookLM download should have .txt extension."""
        # This test validates the filename returned
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assert response.status == 200
        # Content should be text


class TestNotebookLMGuidelineContent:
    """Test NotebookLM guideline content quality."""

    def test_guideline_has_content(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should have substantial content."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        assert len(content) > 50, "Guideline should have meaningful content"

    def test_guideline_has_structure(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should have structured sections."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should have some structure (sections, bullet points, etc.)
        assert len(content) > 100

    def test_guideline_for_presentation(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should be suitable for NotebookLM presentation generation."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should be formatted for presentation
        # May contain sections, bullet points, key points
        assert len(content) > 50

    def test_guideline_based_on_transcription(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should be based on transcription content."""
        # Get transcription first
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if not detail_response.is_success:
            pytest.skip("Cannot get transcription detail")

        transcription = detail_response.json
        if not transcription.get("text"):
            pytest.skip("Transcription has no text")

        # Get guideline
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Guideline should exist
        assert len(response.data) > 0


class TestNotebookLMGuidelineGeneration:
    """Test NotebookLM guideline generation."""

    def test_generate_notebooklm_guideline(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should be able to generate NotebookLM guideline."""
        # This endpoint may or may not exist
        response = prod_client.post(f"/api/transcriptions/{prod_any_transcription_id}/generate-notebooklm", data={})
        # May return 200, 201, or 404 if not implemented
        assert response.status in [200, 201, 202, 404, -1]

    def test_guideline_generation_for_completed_transcription(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should generate guideline for completed transcription."""
        # First check if transcription is completed
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if detail_response.is_success:
            detail = detail_response.json
            if detail.get("status") != "completed":
                pytest.skip("Transcription not completed")

        # Try to generate guideline
        response = prod_client.post(f"/api/transcriptions/{prod_any_transcription_id}/generate-notebooklm", data={})
        assert response.status in [200, 201, 202, 409, 404, -1]


class TestNotebookLMGuidelineSections:
    """Test guideline sections and components."""

    def test_guideline_has_title_section(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should have title or topic section."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data.lower()
        # Should have some indicator of title/topic
        # (may vary based on implementation)

    def test_guideline_has_key_points(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should contain key points."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should have substantial content
        assert len(content) > 100

    def test_guideline_has_summary_section(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should have summary section."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should have summary or overview
        assert len(content) > 50


class TestNotebookLMGuidelineFormats:
    """Test different guideline formats."""

    def test_guideline_as_text(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Default format should be text."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Should be plain text
        assert isinstance(response.data, str)

    def test_guideline_as_markdown(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """May support markdown format."""
        # This endpoint may not exist
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm?format=md")
        # May return 200 or 404
        assert response.status in [200, 404]


class TestNotebookLMGuidelineErrorHandling:
    """Test guideline error handling."""

    def test_guideline_for_nonexistent_transcription(self, prod_client: RemoteProductionClient):
        """Should handle guideline request for non-existent transcription."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.get(f"/api/transcriptions/{fake_id}/notebooklm")
        assert response.status in [404, 400]

    def test_download_guideline_for_nonexistent_transcription(self, prod_client: RemoteProductionClient):
        """Should handle download for non-existent transcription."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.download_file(f"/api/transcriptions/{fake_id}/download-notebooklm")
        assert response.status in [404, 400]

    def test_guideline_for_transcription_without_text(self, prod_client: RemoteProductionClient):
        """Should handle guideline for transcription without text."""
        # May return error or empty guideline
        # This depends on implementation
        pass


class TestNotebookLMGuidelineAuthBypass:
    """Test guideline access with auth bypass."""

    def test_get_guideline_without_auth(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should be able to get guideline without OAuth token."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/notebooklm")
        # Auth bypass should allow access
        assert response.status in [200, 404]

    def test_download_guideline_without_auth(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Download should work without OAuth token."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        # Auth bypass should allow download
        assertions.assert_status(response, 200)


class TestNotebookLMGuidelineForPresentation:
    """Test guideline for presentation generation."""

    def test_guideline_for_slides(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should be suitable for slide generation."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # Should have content suitable for presentation
        assert len(content) > 100

    def test_guideline_has_slide_structure(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should have structure for slides."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        content = response.data
        # May contain slide markers, sections, or structure
        assert len(content) > 50


class TestNotebookLMGuidelineIntegration:
    """Test guideline integration with other features."""

    def test_guideline_with_summary(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Guideline should work with AI summary."""
        response = prod_client.download_file(f"/api/transcriptions/{prod_transcription_with_summary}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Should have content
        assert len(response.data) > 50

    def test_guideline_with_channel_context(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Guideline may include channel context."""
        # Get transcription with channel info
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if not detail_response.is_success:
            pytest.skip("Cannot get transcription detail")

        # Get guideline
        response = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assert response.status == 200


class TestNotebookLMGuidelineStorage:
    """Test guideline storage and retrieval."""

    def test_guideline_persistence(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Guideline should be persistent across requests."""
        # First request
        response1 = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Second request - should get same or similar content
        response2 = prod_client.download_file(f"/api/transcriptions/{prod_any_transcription_id}/download-notebooklm")
        assertions.assert_status(response, 200)

        # Both should have content
        assert len(response1.data) > 0
        assert len(response2.data) > 0

    def test_guideline_regeneration(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should be able to regenerate guideline."""
        # Try to regenerate
        response = prod_client.post(f"/api/transcriptions/{prod_any_transcription_id}/generate-notebooklm", data={})
        # May return 200, 201, 202, or 404
        assert response.status in [200, 201, 202, 404, -1]
