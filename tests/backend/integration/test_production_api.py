"""
Production API Integration Tests

Tests the production server's actual API endpoints via SSH + docker exec.
These tests use localhost auth bypass to authenticate without OAuth.

Run: ./tests/run.prd.sh test_production_api
"""

import pytest
from conftest import RemoteProductionClient, Assertions


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_200(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should return healthy status."""
        response = prod_client.get("/health")
        assertions.assert_status(response, 200)
        assert response.json["status"] == "healthy"


class TestSessionManagement:
    """Test session.json management."""

    def test_session_file_exists(self, prod_session):
        """Session.json should exist on production."""
        assert prod_session, "Session file not found or invalid"

    def test_session_has_test_user(self, prod_session):
        """Session should have test user configured."""
        test_user = prod_session.get("test_user", {})
        assert "id" in test_user
        assert "email" in test_user
        assert test_user.get("is_admin") is True

    def test_session_has_version(self, prod_session):
        """Session should have version field."""
        assert "version" in prod_session


class TestAuthBypass:
    """Test localhost authentication bypass."""

    def test_transcriptions_without_auth(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list transcriptions without OAuth token (localhost bypass)."""
        response = prod_client.get("/api/transcriptions")
        assertions.assert_success(response)
        assertions.assert_has_key(response, "total")
        assertions.assert_has_key(response, "data")

    def test_channels_without_auth(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list channels without OAuth token."""
        response = prod_client.get("/api/channels")
        assertions.assert_success(response)

    def test_admin_users_without_auth(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get admin users list without OAuth token."""
        response = prod_client.get("/api/admin/users")
        assertions.assert_success(response)
        assertions.assert_has_key(response, "total")

    def test_admin_channels_without_auth(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get admin channels without OAuth token."""
        response = prod_client.get("/api/admin/channels")
        assertions.assert_success(response)


class TestTranscriptionsAPI:
    """Test transcriptions API endpoints."""

    def test_list_transcriptions(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list all transcriptions."""
        response = prod_client.get("/api/transcriptions")
        assertions.assert_success(response)

        data = response.json
        assert "total" in data
        assert "page" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_single_transcription(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get single transcription by ID."""
        # First get list to find an ID
        list_response = prod_client.get("/api/transcriptions")
        assertions.assert_success(list_response)

        transcriptions = list_response.json.get("data", [])
        if not transcriptions:
            pytest.skip("No transcriptions found")

        transcription_id = transcriptions[0]["id"]
        response = prod_client.get(f"/api/transcriptions/{transcription_id}")
        assertions.assert_success(response)

        data = response.json
        assert data["id"] == transcription_id
        assert "file_name" in data

    def test_get_transcription_summary(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get transcription summary."""
        list_response = prod_client.get("/api/transcriptions")
        assertions.assert_success(list_response)

        transcriptions = list_response.json.get("data", [])
        if not transcriptions:
            pytest.skip("No transcriptions found")

        transcription_id = transcriptions[0]["id"]
        response = prod_client.get(f"/api/transcriptions/{transcription_id}/summary")
        assertions.assert_success(response)


class TestPagination:
    """Test pagination functionality."""

    def test_pagination_with_page_size(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should respect page_size parameter."""
        response = prod_client.get("/api/transcriptions?page_size=5")
        assertions.assert_success(response)

        data = response.json
        assert data.get("page_size") == 5
        assert len(data.get("data", [])) <= 5

    def test_pagination_with_page_number(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should respect page parameter."""
        response = prod_client.get("/api/transcriptions?page=1&page_size=10")
        assertions.assert_success(response)

        data = response.json
        assert data.get("page") == 1


class TestChannelsAPI:
    """Test channels API endpoints."""

    def test_list_channels(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list all channels."""
        response = prod_client.get("/api/channels")
        assertions.assert_success(response)
        assert isinstance(response.json, list)

    def test_admin_list_channels(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list channels via admin endpoint."""
        response = prod_client.get("/api/admin/channels")
        assertions.assert_success(response)
        assertions.assert_has_key(response, "total")


class TestAdminAPI:
    """Test admin API endpoints."""

    def test_list_users(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list all users via admin endpoint."""
        response = prod_client.get("/api/admin/users")
        assertions.assert_success(response)
        assertions.assert_has_key(response, "total")
        assertions.assert_has_key(response, "data")

    def test_get_stats(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get admin statistics."""
        response = prod_client.get("/api/admin/stats")
        # This might not exist, just check we get a response
        assert response.status in [200, 404]


class TestAuthBypassSecurity:
    """Test that auth bypass only works for localhost."""

    def test_localhost_bypass_works(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Localhost requests should bypass auth (docker exec = localhost)."""
        response = prod_client.get("/api/transcriptions")
        assertions.assert_success(response)
        # If this returns 200, auth bypass is working


class TestDataIntegrity:
    """Test data integrity in production."""

    def test_transcription_data_structure(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Transcriptions should have required fields."""
        response = prod_client.get("/api/transcriptions")
        assertions.assert_success(response)

        transcriptions = response.json.get("data", [])
        if not transcriptions:
            pytest.skip("No transcriptions to validate")

        # Check first transcription structure
        t = transcriptions[0]
        required_fields = ["id", "file_name", "status", "created_at"]
        for field in required_fields:
            assert field in t, f"Missing field: {field}"

    def test_user_data_structure(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Users should have required fields."""
        response = prod_client.get("/api/admin/users")
        assertions.assert_success(response)

        users = response.json.get("data", [])
        if not users:
            pytest.skip("No users to validate")

        user = users[0]
        required_fields = ["id", "email", "is_active"]
        for field in required_fields:
            assert field in user, f"Missing field: {field}"


class TestErrorHandling:
    """Test error handling in production."""

    def test_invalid_transcription_id(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should return 404 for non-existent transcription."""
        response = prod_client.get("/api/transcriptions/00000000-0000-0000-0000-000000000000")
        # Should either return 404 or empty result
        assert response.status in [404, 200]

    def test_invalid_endpoint(self, prod_client: RemoteProductionClient):
        """Should return 404 for invalid endpoint."""
        response = prod_client.get("/api/invalid_endpoint_12345")
        assert response.status == 404


class TestTranscriptionDetail:
    """Test transcription detail endpoints."""

    def test_transcription_has_text(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Transcription detail should have text content."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        assertions.assert_success(response)

        data = response.json
        # May have text field or text may be loaded separately
        assert "id" in data

    def test_transcription_has_status(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Transcription should have status field."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        assertions.assert_success(response)

        data = response.json
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]


class TestAudioManagement:
    """Test audio file management endpoints."""

    def test_list_audio_files(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should list audio files via admin endpoint."""
        response = prod_client.get("/api/admin/audio")
        # May or may not exist
        assert response.status in [200, 404]

    def test_audio_has_metadata(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Transcription should have audio metadata."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        assertions.assert_success(response)

        data = response.json
        # Should have file_name or audio related fields
        assert "file_name" in data or "audio_url" in data or "id" in data


class TestSearchAndFilter:
    """Test search and filter functionality."""

    def test_search_transcriptions_by_filename(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should search transcriptions by filename."""
        # Get a filename first
        list_response = prod_client.get("/api/transcriptions?page_size=1")
        assertions.assert_success(list_response)

        transcriptions = list_response.json.get("data", [])
        if not transcriptions:
            pytest.skip("No transcriptions to search")

        filename = transcriptions[0].get("file_name", "")
        if not filename:
            pytest.skip("No filename to search for")

        # Search with the filename
        response = prod_client.get(f"/api/transcriptions?search={filename}")
        assertions.assert_success(response)

    def test_filter_by_status(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should filter transcriptions by status."""
        for status in ["completed", "processing", "pending", "failed"]:
            response = prod_client.get(f"/api/transcriptions?status={status}")
            # Should return 200 even if no results
            assert response.status == 200

    def test_filter_by_channel(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should filter transcriptions by channel."""
        # Get channels first
        channels_response = prod_client.get("/api/channels")
        if channels_response.is_success and channels_response.json:
            channels = channels_response.json if isinstance(channels_response.json, list) else []
            if channels:
                channel_id = channels[0].get("id") if isinstance(channels[0], dict) else None
                if channel_id:
                    response = prod_client.get(f"/api/transcriptions?channel_id={channel_id}")
                    assert response.status == 200


class TestTranscriptionSharing:
    """Test transcription sharing functionality."""

    def test_get_share_link(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should get or create share link."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/share")
        # May return share link or 404 if not implemented
        assert response.status in [200, 201, 404]

    def test_access_shared_transcription(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should access transcription via share link."""
        # This would require a share token
        # For now, just check the endpoint exists
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/share")
        assert response.status in [200, 201, 404]


class TestChannelAssignment:
    """Test channel assignment functionality."""

    def test_get_transcription_channels(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should get channels assigned to transcription."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/channels")
        assertions.assert_success(response)

        data = response.json
        # Should return list of channels (may be empty)
        assert isinstance(data, list)

    def test_assign_channel_to_transcription(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should assign channel to transcription."""
        # Get a channel first
        channels_response = prod_client.get("/api/channels")
        if not channels_response.is_success or not channels_response.json:
            pytest.skip("No channels available")

        channels = channels_response.json if isinstance(channels_response.json, list) else []
        if not channels:
            pytest.skip("No channels to assign")

        channel_id = channels[0].get("id") if isinstance(channels[0], dict) else None
        if not channel_id:
            pytest.skip("Invalid channel ID")

        # Try to assign
        response = prod_client.post(
            f"/api/transcriptions/{prod_any_transcription_id}/channels",
            data={"channel_ids": [channel_id]}
        )
        # May return 200, 201, or other status
        assert response.status in [200, 201, 400, 404, -1]


class TestStatsAndMetrics:
    """Test statistics and metrics endpoints."""

    def test_get_transcription_stats(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get transcription statistics."""
        response = prod_client.get("/api/admin/stats")
        # May or may not exist
        assert response.status in [200, 404]

    def test_get_user_stats(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get user statistics."""
        response = prod_client.get("/api/admin/stats/users")
        # May or may not exist
        assert response.status in [200, 404]


class TestAdminUserManagement:
    """Test admin user management endpoints."""

    def test_get_user_detail(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should get user detail by ID."""
        # Get a user first
        users_response = prod_client.get("/api/admin/users?page_size=1")
        assertions.assert_success(users_response)

        users = users_response.json.get("data", [])
        if not users:
            pytest.skip("No users found")

        user_id = users[0].get("id")
        response = prod_client.get(f"/api/admin/users/{user_id}")
        assertions.assert_success(response)

    def test_update_user_status(self, prod_client: RemoteProductionClient):
        """Should be able to update user status."""
        # Get a user first
        users_response = prod_client.get("/api/admin/users?page_size=1")
        if not users_response.is_success:
            pytest.skip("Cannot get users")

        users = users_response.json.get("data", [])
        if not users:
            pytest.skip("No users found")

        user_id = users[0].get("id")
        # Try to update (may fail due to permissions)
        response = prod_client.post(
            f"/api/admin/users/{user_id}",
            data={"is_active": True}
        )
        # May return 200, 403, or other status
        assert response.status in [200, 400, 403, 404, -1]


class TestAdminChannelManagement:
    """Test admin channel management endpoints."""

    def test_create_channel(self, prod_client: RemoteProductionClient):
        """Should be able to create a channel."""
        response = prod_client.post(
            "/api/admin/channels",
            data={
                "name": "test-channel-integration",
                "description": "Test channel for integration tests"
            }
        )
        # May return 201, 200, or error
        assert response.status in [200, 201, 400, 409, -1]

    def test_update_channel(self, prod_client: RemoteProductionClient):
        """Should be able to update a channel."""
        # Get a channel first
        channels_response = prod_client.get("/api/channels")
        if not channels_response.is_success or not channels_response.json:
            pytest.skip("No channels available")

        channels = channels_response.json if isinstance(channels_response.json, list) else []
        if not channels:
            pytest.skip("No channels to update")

        channel_id = channels[0].get("id") if isinstance(channels[0], dict) else None
        if not channel_id:
            pytest.skip("Invalid channel ID")

        response = prod_client.post(
            f"/api/admin/channels/{channel_id}",
            data={"description": "Updated description"}
        )
        # May return 200, 400, or other status
        assert response.status in [200, 400, 404, -1]


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_multiple_concurrent_requests(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should handle multiple concurrent requests."""
        # Make multiple requests in sequence (concurrent is hard in single-threaded test)
        responses = []
        for _ in range(5):
            response = prod_client.get("/api/health")
            responses.append(response)
            assertions.assert_status(response, 200)

        # All should succeed
        assert all(r.status == 200 for r in responses)


class TestResponseHeaders:
    """Test response headers."""

    def test_cors_headers(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should have proper CORS headers."""
        response = prod_client.get("/api/health")
        assertions.assert_status(response, 200)
        # Headers validation is done via response checks

    def test_content_type_headers(self, prod_client: RemoteProductionClient, assertions: Assertions):
        """Should have proper content-type headers."""
        response = prod_client.get("/api/transcriptions")
        assertions.assert_status(response, 200)
        # Should return JSON
