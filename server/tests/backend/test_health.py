"""
Test suite for Health Check endpoint.

Tests for:
- GET /health - Basic health check
- GET /api/health - Alternative health endpoint (if exists)
- Service availability checks
"""
import pytest
from fastapi import status as http_status


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_returns_200(self, test_client):
        """Test that /health endpoint returns 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == http_status.HTTP_200_OK

    def test_health_returns_json(self, test_client):
        """Test that /health endpoint returns JSON with status."""
        response = test_client.get("/health")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_includes_service_name(self, test_client):
        """Test that /health endpoint includes service identifier."""
        response = test_client.get("/health")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        assert "service" in data
        assert "whisper" in data["service"].lower()

    def test_health_no_auth_required(self, test_client):
        """Test that /health endpoint does not require authentication."""
        # Should work without auth headers
        response = test_client.get("/health")

        assert response.status_code == http_status.HTTP_200_OK
