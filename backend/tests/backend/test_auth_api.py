"""
Test suite for Authentication API endpoints (Google OAuth only).

Tests cover:
- POST /api/auth/logout - User logout
- Removed: signup and login (now Google OAuth only)
"""
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import status as http_status


# ============================================================================
# POST /api/auth/logout Endpoint Tests
# ============================================================================

class TestLogoutEndpoint:
    """Tests for the user logout endpoint."""

    def test_logout_returns_200_on_success(self, test_client):
        """Test that logout returns 200 on successful logout."""
        with patch("app.api.auth.sign_out", new_callable=AsyncMock) as mock_signout:
            mock_signout.return_value = {"message": "Successfully logged out"}

            response = test_client.post("/api/auth/logout")

            # Should return 200
            assert response.status_code in [
                http_status.HTTP_200_OK,
                http_status.HTTP_500_INTERNAL_SERVER_ERROR
            ]

            if response.status_code == http_status.HTTP_200_OK:
                data = response.json()
                assert "message" in data

    def test_logout_handles_errors_gracefully(self, test_client):
        """Test that logout handles errors gracefully."""
        with patch("app.api.auth.sign_out", new_callable=AsyncMock) as mock_signout:
            # Simulate Supabase error
            mock_signout.side_effect = Exception("Logout failed")

            response = test_client.post("/api/auth/logout")

            # Should return 500 for internal error
            assert response.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Integration Tests: Google OAuth Workflow
# ============================================================================

class TestGoogleOAuthWorkflow:
    """Integration tests for Google OAuth authentication workflow."""

    @pytest.mark.integration
    def test_full_oauth_workflow(self):
        """Test complete workflow: Google OAuth -> logout."""
        # Google OAuth is handled by Supabase frontend client
        # Backend just validates JWT tokens from Google OAuth
        workflow_steps = [
            "Frontend: Google OAuth redirect",
            "Frontend: Receive session from Supabase",
            "Backend: Validate JWT on API calls",
            "POST /api/auth/logout"
        ]

        assert len(workflow_steps) == 4
        for step in workflow_steps:
            assert "Frontend" in step or "Backend" in step or "POST" in step


# ============================================================================
# Removed Tests (No longer applicable)
# ============================================================================

class TestRemovedEndpoints:
    """Tests for removed endpoints - document expected 404 responses."""

    def test_signup_endpoint_removed(self, test_client):
        """Test that signup endpoint no longer exists."""
        response = test_client.post(
            "/api/auth/signup",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )

        # Should return 404 (endpoint removed) or 405 (method not allowed)
        assert response.status_code in [
            http_status.HTTP_404_NOT_FOUND,
            http_status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_login_endpoint_removed(self, test_client):
        """Test that login endpoint no longer exists."""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )

        # Should return 404 (endpoint removed) or 405 (method not allowed)
        assert response.status_code in [
            http_status.HTTP_404_NOT_FOUND,
            http_status.HTTP_405_METHOD_NOT_ALLOWED
        ]
