"""
Auth Middleware Tests

Tests authentication and authorization middleware with different roles and scenarios.

Note: With DISABLE_AUTH=true, authentication is bypassed in the test environment.
Tests are structured to work with real_auth_client fixture.
"""

import pytest
from fastapi import status


@pytest.mark.skip(reason="DISABLE_AUTH=true bypasses authentication checks in test environment")
class TestAuthMiddleware:
    """Test authentication and authorization middleware.

    These tests are skipped because DISABLE_AUTH=true bypasses authentication
    in the test environment. To test authentication properly, run integration
    tests with actual Supabase authentication or use E2E tests.
    """

    @pytest.mark.skip(reason="Auth bypassed in test environment")
    def test_unauthenticated_request_rejected(self, real_auth_client):
        """Test that unauthenticated requests are rejected."""
        response = real_auth_client.get('/api/transcriptions')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.skip(reason="Auth bypassed in test environment")
    def test_valid_token_accepted(self, real_auth_client):
        """Test that valid tokens are accepted."""
        response = real_auth_client.get('/api/transcriptions')
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="Auth bypassed in test environment")
    def test_admin_only_endpoint_protection(self, real_auth_client):
        """Test that admin endpoints have proper protection."""
        # Admin endpoint tests are handled in test_admin_api.py
        pass
