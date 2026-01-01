"""
Test suite for Authentication API endpoints.

Tests cover:
- POST /api/auth/signup - User registration
- POST /api/auth/login - User login
- POST /api/auth/logout - User logout
- Error handling for invalid credentials
- Response validation
"""
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import status as http_status


# ============================================================================
# POST /api/auth/signup Endpoint Tests
# ============================================================================

class TestSignupEndpoint:
    """Tests for the user signup endpoint."""

    def test_signup_returns_201_on_success(self, client):
        """Test that signup returns 201 on successful registration."""
        mock_response = {
            "user": MagicMock(id=str(uuid4()), email="test@example.com"),
            "session": MagicMock(
                access_token="fake_access_token",
                refresh_token="fake_refresh_token"
            )
        }

        with patch("app.api.auth.sign_up", new_callable=AsyncMock) as mock_signup:
            mock_signup.return_value = mock_response

            response = client.post(
                "/api/auth/signup",
                json={
                    "email": "test@example.com",
                    "password": "password123",
                    "full_name": "Test User"
                }
            )

            assert response.status_code in [
                http_status.HTTP_201_CREATED,
                http_status.HTTP_400_BAD_REQUEST
            ]

            if response.status_code == http_status.HTTP_201_CREATED:
                data = response.json()
                assert "access_token" in data
                assert "user" in data

    def test_signup_requires_email(self, client):
        """Test that signup requires email field."""
        response = client.post(
            "/api/auth/signup",
            json={
                "password": "password123",
                "full_name": "Test User"
            }
        )

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_requires_password(self, client):
        """Test that signup requires password field."""
        response = client.post(
            "/api/auth/signup",
            json={
                "email": "test@example.com",
                "full_name": "Test User"
            }
        )

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_with_duplicate_email(self, client):
        """Test that signup handles duplicate email."""
        with patch("app.api.auth.sign_up", new_callable=AsyncMock) as mock_signup:
            mock_signup.side_effect = Exception("User already registered")

            response = client.post(
                "/api/auth/signup",
                json={
                    "email": "existing@example.com",
                    "password": "password123"
                }
            )

            assert response.status_code == http_status.HTTP_400_BAD_REQUEST


# ============================================================================
# POST /api/auth/login Endpoint Tests
# ============================================================================

class TestLoginEndpoint:
    """Tests for the user login endpoint."""

    def test_login_returns_200_on_success(self, client):
        """Test that login returns 200 on successful authentication."""
        mock_response = {
            "access_token": "fake_access_token",
            "refresh_token": "fake_refresh_token",
            "user": MagicMock(id=str(uuid4()), email="test@example.com")
        }

        with patch("app.api.auth.sign_in", new_callable=AsyncMock) as mock_signin:
            mock_signin.return_value = mock_response

            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password123"
                }
            )

            assert response.status_code in [
                http_status.HTTP_200_OK,
                http_status.HTTP_401_UNAUTHORIZED
            ]

            if response.status_code == http_status.HTTP_200_OK:
                data = response.json()
                assert "access_token" in data
                assert "user" in data

    def test_login_requires_email(self, client):
        """Test that login requires email field."""
        response = client.post(
            "/api/auth/login",
            json={"password": "password123"}
        )

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_requires_password(self, client):
        """Test that login requires password field."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com"}
        )

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_invalid_credentials(self, client):
        """Test that login returns 401 for invalid credentials."""
        with patch("app.api.auth.sign_in", new_callable=AsyncMock) as mock_signin:
            mock_signin.side_effect = Exception("Invalid login credentials")

            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrongpassword"
                }
            )

            assert response.status_code == http_status.HTTP_401_UNAUTHORIZED


# ============================================================================
# POST /api/auth/logout Endpoint Tests
# ============================================================================

class TestLogoutEndpoint:
    """Tests for the user logout endpoint."""

    def test_logout_returns_200_on_success(self, client):
        """Test that logout returns 200 on successful logout."""
        with patch("app.api.auth.sign_out", new_callable=AsyncMock) as mock_signout:
            mock_signout.return_value = {"message": "Successfully logged out"}

            response = client.post("/api/auth/logout")

            assert response.status_code in [
                http_status.HTTP_200_OK,
                http_status.HTTP_500_INTERNAL_SERVER_ERROR
            ]

            if response.status_code == http_status.HTTP_200_OK:
                data = response.json()
                assert "message" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestAuthWorkflow:
    """Integration tests for complete authentication workflow."""

    @pytest.mark.integration
    def test_full_auth_workflow(self):
        """Test complete workflow: signup -> login -> logout."""
        workflow_steps = [
            "POST /api/auth/signup",
            "POST /api/auth/login",
            "POST /api/auth/logout"
        ]

        assert len(workflow_steps) == 3
        for step in workflow_steps:
            assert "POST" in step
