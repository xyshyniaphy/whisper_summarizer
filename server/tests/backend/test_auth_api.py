"""
Tests for Auth API endpoints.

Tests authentication-related endpoints (logout, etc.).
"""

import pytest
from unittest.mock import patch, AsyncMock


# ============================================================================
# Logout (POST /api/auth/logout)
# ============================================================================

def test_logout_success(test_client):
    """Test successful logout."""
    response = test_client.post("/api/auth/logout")
    # Logout endpoint returns 200 with success message
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@patch("app.api.auth.sign_out")
def test_logout_with_supabase_error(mock_sign_out, test_client):
    """Test logout when Supabase sign_out throws an error."""
    # Mock sign_out to raise an exception
    mock_sign_out.side_effect = Exception("Supabase connection error")

    response = test_client.post("/api/auth/logout")
    # Should return 500 when Supabase fails
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@patch("app.api.auth.sign_out")
def test_logout_with_supabase_success(mock_sign_out, test_client):
    """Test logout with successful Supabase sign_out."""
    # Mock sign_out to return success
    mock_sign_out.return_value = AsyncMock()
    mock_sign_out.return_value = {"message": "ログアウトしました"}

    response = test_client.post("/api/auth/logout")
    assert response.status_code == 200
