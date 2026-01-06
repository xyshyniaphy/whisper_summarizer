"""
Users API Unit Tests

Unit tests for user endpoints that mock dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.api.users import get_me, update_me
from app.models.user import User


# ============================================================================
# get_me() Tests
# ============================================================================

class TestGetMe:
    """Test get_me endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_user_info(self):
        """Should return current user information."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False,
            activated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )

        result = await get_me(user)

        assert result["email"] == "test@example.com"
        assert result["is_active"] is True
        assert result["is_admin"] is False
        assert "id" in result
        assert "activated_at" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_should_return_admin_status(self):
        """Should include admin status in response."""
        user = User(
            id=uuid4(),
            email="admin@example.com",
            is_active=True,
            is_admin=True,
            activated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )

        result = await get_me(user)

        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_should_convert_uuid_to_string(self):
        """Should convert UUID to string for JSON serialization."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            is_active=True,
            is_admin=False
        )

        result = await get_me(user)

        assert isinstance(result["id"], str)
        assert result["id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_should_handle_null_activated_at(self):
        """Should handle user without activation timestamp."""
        user = User(
            id=uuid4(),
            email="pending@example.com",
            is_active=False,
            is_admin=False,
            activated_at=None,
            created_at=datetime.now(timezone.utc)
        )

        result = await get_me(user)

        assert result["activated_at"] is None
        assert result["is_active"] is False


# ============================================================================
# update_me() Tests
# ============================================================================

class TestUpdateMe:
    """Test update_me endpoint."""

    @pytest.mark.asyncio
    @patch('app.api.users.logger')
    async def test_should_return_success_message(self, mock_logger):
        """Should return success message (placeholder implementation)."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        mock_db = MagicMock()

        result = await update_me("Updated Name", mock_db, user)

        assert result["message"] == "ユーザー情報を更新しました"
        assert "full_name" not in result  # Currently just returns success message

    @pytest.mark.asyncio
    async def test_should_accept_full_name_parameter(self):
        """Should accept full_name parameter."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        mock_db = MagicMock()

        result = await update_me("Test User", mock_db, user)

        assert result is not None

    @pytest.mark.asyncio
    async def test_should_handle_empty_full_name(self):
        """Should handle empty full name."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        mock_db = MagicMock()

        result = await update_me("", mock_db, user)

        assert result["message"] == "ユーザー情報を更新しました"

    @pytest.mark.asyncio
    async def test_should_handle_unicode_full_name(self):
        """Should handle unicode characters in full name."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False
        )
        mock_db = MagicMock()

        result = await update_me("テストユーザー", mock_db, user)

        assert result is not None


# ============================================================================
# Edge Cases
# ============================================================================

class TestUsersEdgeCases:
    """Test edge cases for user endpoints."""

    @pytest.mark.asyncio
    async def test_should_handle_user_with_no_activation(self):
        """Should handle user that hasn't been activated."""
        user = User(
            id=uuid4(),
            email="pending@example.com",
            is_active=False,
            is_admin=False,
            activated_at=None,
            created_at=datetime.now(timezone.utc)
        )

        result = await get_me(user)

        assert result["is_active"] is False
        assert result["activated_at"] is None

    @pytest.mark.asyncio
    async def test_should_include_all_required_fields(self):
        """Should include all required fields in user response."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            is_active=True,
            is_admin=False,
            activated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )

        result = await get_me(user)

        required_fields = ["id", "email", "is_active", "is_admin", "activated_at", "created_at"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
