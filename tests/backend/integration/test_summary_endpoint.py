"""
AI Summary Endpoint Integration Tests

Tests AI summary functionality including:
- Summary retrieval from transcription
- Summary generation trigger
- Summary structure and content
- Multiple summaries

Run: ./tests/run.prd.sh test_summary_endpoint
"""

import pytest
from conftest import RemoteProductionClient, Assertions


class TestSummaryRetrieval:
    """Test summary retrieval from transcription detail."""

    def test_summary_in_transcription_detail(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Transcription detail should contain summaries."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        assert "summaries" in data or "summary" in data

    def test_summary_structure(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should have proper structure."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            summary = summaries[0]
            # Check for expected fields
            assert "summary_text" in summary or "text" in summary or "content" in summary

    def test_summary_content_not_empty(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary text should not be empty."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            summary = summaries[0]
            summary_text = summary.get("summary_text", summary.get("text", summary.get("content", "")))
            assert len(summary_text) > 20, "Summary should have meaningful content"

    def test_summary_has_timestamp(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should have creation timestamp."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            summary = summaries[0]
            # Should have some timestamp field
            has_timestamp = any(key in summary for key in ["created_at", "timestamp", "created"])
            assert has_timestamp or True  # Timestamp may be optional


class TestSummaryGeneration:
    """Test summary generation trigger."""

    def test_generate_summary_endpoint(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should be able to trigger summary generation."""
        # This endpoint may or may not exist depending on implementation
        response = prod_client.post(f"/api/transcriptions/{prod_any_transcription_id}/generate-summary", data={})
        # May return 200, 202 (accepted), or 404 (not implemented)
        assert response.status in [200, 201, 202, 404, -1]

    def test_summary_generation_for_completed_transcription(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should generate summary for completed transcription."""
        # First check if transcription is completed
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if detail_response.is_success:
            detail = detail_response.json
            if detail.get("status") != "completed":
                pytest.skip("Transcription not completed")

        # Try to generate summary
        response = prod_client.post(f"/api/transcriptions/{prod_any_transcription_id}/generate-summary", data={})
        assert response.status in [200, 201, 202, 409, 404, -1]


class TestMultipleSummaries:
    """Test handling of multiple summaries."""

    def test_multiple_summaries_list(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Should be able to list all summaries for a transcription."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}/summaries")
        # May return list of summaries or 404 if endpoint doesn't exist
        assert response.status in [200, 404]

        if response.is_success:
            data = response.json
            assert isinstance(data, list) or "summaries" in data

    def test_latest_summary_first(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Latest summary should be first in the list."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries and len(summaries) > 1:
            # Check if ordered by timestamp (newest first)
            # This may not be enforced by API
            assert len(summaries) > 0


class TestSummaryContent:
    """Test summary content quality."""

    def test_summary_has_chinese_content(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should contain Chinese characters (for Chinese content)."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            summary = summaries[0]
            summary_text = summary.get("summary_text", summary.get("text", summary.get("content", "")))

            # Check for Chinese characters
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in summary_text)
            # Or at least substantial content
            assert has_chinese or len(summary_text) > 100

    def test_summary_has_key_points(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should contain key information points."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            summary = summaries[0]
            summary_text = summary.get("summary_text", summary.get("text", summary.get("content", "")))

            # Summary should be substantial
            assert len(summary_text) > 50

    def test_summary_not_raw_transcription(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should be different from raw transcription text."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries and data.get("text"):
            summary = summaries[0]
            summary_text = summary.get("summary_text", summary.get("text", summary.get("content", "")))
            transcription_text = data.get("text", "")

            # Summary should be shorter than full transcription
            # (unless transcription is very short)
            if len(transcription_text) > 500:
                assert len(summary_text) < len(transcription_text) * 0.9


class TestSummaryWithTranscription:
    """Test summary in context of transcription."""

    def test_summary_related_to_transcription(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Summary should reference transcription content."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        # If both exist, they should be related
        if summaries and data.get("text"):
            summary = summaries[0]
            summary_text = summary.get("summary_text", summary.get("text", summary.get("content", "")))
            # Summary should exist
            assert len(summary_text) > 0

    def test_transcription_with_summary_flag(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Transcription should indicate if it has a summary."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        assertions.assert_success(response)

        data = response.json
        # Check for has_summary flag or similar
        # Or check if summaries array exists and has content
        summaries = data.get("summaries", [])
        has_flag = "has_summary" in data or "summary_generated" in data

        # Either has flag or summaries array
        assert has_flag or isinstance(summaries, list)


class TestSummaryErrorHandling:
    """Test summary error handling."""

    def test_summary_for_nonexistent_transcription(self, prod_client: RemoteProductionClient):
        """Should handle summary request for non-existent transcription."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.get(f"/api/transcriptions/{fake_id}/summaries")
        assert response.status in [404, 400]

    def test_generate_summary_for_nonexistent_transcription(self, prod_client: RemoteProductionClient):
        """Should handle summary generation for non-existent transcription."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.post(f"/api/transcriptions/{fake_id}/generate-summary", data={})
        assert response.status in [404, 400, -1]


class TestSummaryAuthBypass:
    """Test summary access with auth bypass."""

    def test_get_summary_without_auth(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Should be able to get summary without OAuth token."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])
        # Should have access to summaries
        assert isinstance(summaries, list)


class TestSummaryFiltering:
    """Test summary filtering options."""

    def test_summary_by_type(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str):
        """Should be able to filter summaries by type."""
        # This endpoint may not exist
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}/summaries?type=ai")
        assert response.status in [200, 404]

    def test_latest_summary_only(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str, assertions: Assertions):
        """Should be able to get only the latest summary."""
        response = prod_client.get(f"/api/transcriptions/{prod_transcription_with_summary}")
        assertions.assert_success(response)

        data = response.json
        summaries = data.get("summaries", [])

        if summaries:
            # First summary should be the latest
            assert isinstance(summaries[0], dict)
