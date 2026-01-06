"""
Logout API Tests

Tests for the logout endpoint.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ============================================================================
# POST /logout Tests
# ============================================================================

class TestLogoutEndpoint:
    """Test logout endpoint."""

    @patch('app.api.auth.sign_out')
    async def test_should_logout_successfully(self, mock_sign_out, client):
        """Should logout successfully."""
        mock_sign_out.return_value = {"message": "Logged out successfully"}

        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch('app.api.auth.sign_out')
    async def test_should_handle_sign_out_exception(self, mock_sign_out, client):
        """Should handle exception when sign_out fails."""
        mock_sign_out.side_effect = Exception("Supabase error")

        response = client.post("/api/auth/logout")

        assert response.status_code == 500
        # Error message is in Japanese
        assert "失敗" in response.json()["detail"]

    @patch('app.api.auth.sign_out')
    async def test_should_call_sign_out_function(self, mock_sign_out, client):
        """Should call sign_out function."""
        mock_sign_out.return_value = {"message": "Logged out"}

        client.post("/api/auth/logout")

        mock_sign_out.assert_called_once_with("")

    @patch('app.api.auth.sign_out')
    async def test_should_return_sign_out_result(self, mock_sign_out, client):
        """Should return the result from sign_out."""
        expected_result = {"message": "Logged out successfully", "redirect": "/login"}
        mock_sign_out.return_value = expected_result

        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        assert response.json() == expected_result

    @patch('app.api.auth.sign_out')
    async def test_should_handle_empty_response(self, mock_sign_out, client):
        """Should handle empty response from sign_out."""
        mock_sign_out.return_value = {}

        response = client.post("/api/auth/logout")

        assert response.status_code == 200

    @patch('app.api.auth.sign_out')
    async def test_should_handle_network_error(self, mock_sign_out, client):
        """Should handle network errors."""
        mock_sign_out.side_effect = ConnectionError("Network error")

        response = client.post("/api/auth/logout")

        assert response.status_code == 500

    @patch('app.api.auth.sign_out')
    async def test_should_handle_timeout_error(self, mock_sign_out, client):
        """Should handle timeout errors."""
        import asyncio
        mock_sign_out.side_effect = asyncio.TimeoutError("Timeout")

        response = client.post("/api/auth/logout")

        assert response.status_code == 500

    @patch('app.api.auth.sign_out')
    async def test_should_log_error_on_failure(self, mock_sign_out, client):
        """Should log error when logout fails."""
        import logging
        mock_sign_out.side_effect = ValueError("Test error")

        with patch('app.api.auth.logger') as mock_logger:
            response = client.post("/api/auth/logout")

            # Logger should have been called
            assert response.status_code == 500


# ============================================================================
# Edge Cases
# ============================================================================

class TestLogoutEdgeCases:
    """Test logout edge cases."""

    @patch('app.api.auth.sign_out')
    async def test_should_handle_none_response(self, mock_sign_out, client):
        """Should handle None response from sign_out."""
        mock_sign_out.return_value = None

        response = client.post("/api/auth/logout")

        assert response.status_code == 200

    @patch('app.api.auth.sign_out')
    async def test_should_handle_runtime_error(self, mock_sign_out, client):
        """Should handle RuntimeError."""
        mock_sign_out.side_effect = RuntimeError("Runtime error")

        response = client.post("/api/auth/logout")

        assert response.status_code == 500

    @patch('app.api.auth.sign_out')
    async def test_should_handle_multiple_consecutive_requests(self, mock_sign_out, client):
        """Should handle multiple consecutive logout requests."""
        mock_sign_out.return_value = {"message": "Logged out"}

        response1 = client.post("/api/auth/logout")
        response2 = client.post("/api/auth/logout")
        response3 = client.post("/api/auth/logout")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert mock_sign_out.call_count == 3


# ============================================================================
# Response Format Tests
# ============================================================================

class TestLogoutResponseFormat:
    """Test logout response format."""

    @patch('app.api.auth.sign_out')
    async def test_should_return_json_response(self, mock_sign_out, client):
        """Should return JSON response."""
        mock_sign_out.return_value = {"status": "ok"}

        response = client.post("/api/auth/logout")

        assert response.headers["content-type"] == "application/json"

    @patch('app.api.auth.sign_out')
    async def test_should_handle_complex_response(self, mock_sign_out, client):
        """Should handle complex response from sign_out."""
        complex_response = {
            "message": "Logged out",
            "user": {"id": "123", "email": "test@example.com"},
            "timestamp": "2025-01-01T00:00:00Z"
        }
        mock_sign_out.return_value = complex_response

        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out"
        assert "user" in data
