"""
Tests for Users API endpoints.

Tests current user profile endpoints (GET /me, PUT /me).
"""

import pytest
from uuid import uuid4, UUID

from app.models.user import User


# ============================================================================
# Get Current User (GET /api/users/me)
# ============================================================================

def test_get_me_returns_user_info(test_client, db_session):
    """Test getting current user information."""
    # Create active user in database
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Mock auth as this user
    from app.core.supabase import get_current_user
    from app.main import app

    async def mock_get_current_user():
        return {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = test_client.get("/api/users/me")

    app.dependency_overrides = {}

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "is_active" in data
    assert "is_admin" in data
    assert "activated_at" in data
    assert "created_at" in data


def test_get_me_without_auth(test_client):
    """Test that getting user info without authentication fails."""
    response = test_client.get("/api/users/me")
    # Should return 401 or 403 when not authenticated
    assert response.status_code in [401, 403]


def test_get_me_for_inactive_user(test_client, db_session):
    """Test getting user info for inactive user."""
    # Create inactive user
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174001"),
        email=f"inactive-{uuid4().hex[:8]}@example.com",
        is_active=False,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Mock auth as inactive user
    from app.core.supabase import get_current_user
    from app.main import app

    async def mock_get_current_user():
        return {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = test_client.get("/api/users/me")

    app.dependency_overrides = {}

    # Should return 403 Forbidden for inactive user
    assert response.status_code == 403


# ============================================================================
# Update Current User (PUT /api/users/me)
# ============================================================================

def test_update_me_success(test_client, db_session):
    """Test updating current user information."""
    # Create active user in database
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Mock auth as this user
    from app.core.supabase import get_current_user
    from app.main import app

    async def mock_get_current_user():
        return {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = test_client.put("/api/users/me", params={"full_name": "Test User"})

    app.dependency_overrides = {}

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_update_me_without_auth(test_client):
    """Test that updating user info without authentication fails."""
    response = test_client.put("/api/users/me", params={"full_name": "Test User"})
    # Should return 401 or 403 when not authenticated
    assert response.status_code in [401, 403]


def test_update_me_with_empty_name(test_client, db_session):
    """Test updating user info with empty name."""
    # Create active user in database
    user = User(
        id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        email=f"test-{uuid4().hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()

    # Mock auth as this user
    from app.core.supabase import get_current_user
    from app.main import app

    async def mock_get_current_user():
        return {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = test_client.put("/api/users/me", params={"full_name": ""})

    app.dependency_overrides = {}

    # API currently returns 200 even with empty name (placeholder endpoint)
    assert response.status_code == 200
