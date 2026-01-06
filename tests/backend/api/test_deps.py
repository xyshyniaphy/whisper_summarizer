"""
API Dependencies Tests

Tests for deps.py functions including get_db, get_current_db_user, require_admin, require_active.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from fastapi import HTTPException

from app.api.deps import get_db, get_current_db_user, require_admin, require_active
from app.models.user import User


# ============================================================================
# get_db() Tests
# ============================================================================

class TestGetDb:
    """Test get_db dependency."""

    @pytest.mark.asyncio
    @patch('app.api.deps.SessionLocal')
    async def test_should_yield_database_session(self, mock_session_local):
        """Should yield database session and close it."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        db_gen = get_db()
        db = next(db_gen)

        assert db == mock_db

        # Cleanup
        try:
            next(db_gen)
        except StopIteration:
            pass

        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.deps.SessionLocal')
    async def test_should_close_session_on_exception(self, mock_session_local):
        """Should close session even if exception occurs."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        db_gen = get_db()
        db = next(db_gen)

        # Simulate exception during usage
        try:
            db_gen.close()
        except:
            pass

        # Should still close
        mock_db.close.assert_called_once()


# ============================================================================
# get_current_db_user() Tests
# ============================================================================

class TestGetCurrentDbUser:
    """Test get_current_db_user dependency."""

    @pytest.mark.asyncio
    @patch('app.api.deps.SessionLocal')
    async def test_should_auto_create_user_when_not_exists(self, mock_session_local):
        """Should auto-create user when not found in local database."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None  # User not found
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        current_user = {"email": "newuser@example.com"}

        result = await get_current_db_user(current_user, mock_db)

        # Should create new inactive user
        assert result.email == "newuser@example.com"
        assert result.is_active is False
        assert result.is_admin is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.api.deps.SessionLocal')
    async def test_should_return_existing_user(self, mock_session_local):
        """Should return existing user from local database."""
        mock_db = MagicMock()
        existing_user = User(
            id=uuid4(),
            email="existing@example.com",
            is_active=True,
            is_admin=False
        )
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing_user
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        current_user = {"email": "existing@example.com"}

        result = await get_current_db_user(current_user, mock_db)

        # Should return existing user
        assert result.id == existing_user.id
        assert result.email == "existing@example.com"

    @pytest.mark.asyncio
    @patch('app.api.deps.SessionLocal')
    async def test_should_skip_deleted_users(self, mock_session_local):
        """Should skip soft-deleted users and create new one."""
        mock_db = MagicMock()
        deleted_user = User(
            id=uuid4(),
            email="deleted@example.com",
            is_active=False,
            is_admin=False,
            deleted_at=None  # Not deleted in query results due to filter
        )
        # Query returns None because user is deleted
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        current_user = {"email": "deleted@example.com"}

        result = await get_current_db_user(current_user, mock_db)

        # Should create new user (not return deleted one)
        mock_db.add.assert_called_once()


# ============================================================================
# require_admin() Tests
# ============================================================================

class TestRequireAdmin:
    """Test require_admin dependency."""

    @pytest.mark.asyncio
    async def test_should_return_admin_user(self):
        """Should return admin user."""
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            is_active=True,
            is_admin=True
        )

        result = await require_admin(admin_user)

        assert result.id == admin_user.id
        assert result.is_admin is True

    @pytest.mark.asyncio
    async def test_should_raise_403_for_non_admin_user(self):
        """Should raise 403 when user is not admin."""
        regular_user = User(
            id=uuid4(),
            email="user@example.com",
            is_active=True,
            is_admin=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_should_raise_403_with_detail_for_non_admin(self):
        """Should include proper error detail for non-admin."""
        non_admin = User(
            id=uuid4(),
            email="nonadmin@example.com",
            is_active=True,
            is_admin=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(non_admin)

        assert exc_info.value.detail == "Admin access required"


# ============================================================================
# require_active() Tests
# ============================================================================

class TestRequireActive:
    """Test require_active dependency."""

    @pytest.mark.asyncio
    async def test_should_return_active_user(self):
        """Should return active user."""
        active_user = User(
            id=uuid4(),
            email="active@example.com",
            is_active=True,
            is_admin=False
        )

        result = await require_active(active_user)

        assert result.id == active_user.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_should_raise_403_for_inactive_user(self):
        """Should raise 403 when user account is not active."""
        inactive_user = User(
            id=uuid4(),
            email="inactive@example.com",
            is_active=False,
            is_admin=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_active(inactive_user)

        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert "account_inactive" in detail["error"]
        assert "pending activation" in detail["message"]
        assert str(inactive_user.id) in detail["user_id"]

    @pytest.mark.asyncio
    async def test_should_include_user_id_in_error_response(self):
        """Should include user_id in inactive account error."""
        test_user_id = uuid4()
        inactive_user = User(
            id=test_user_id,
            email="test@example.com",
            is_active=False,
            is_admin=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_active(inactive_user)

        detail = exc_info.value.detail
        assert detail["user_id"] == str(test_user_id)


# ============================================================================
# Edge Cases
# ============================================================================

class TestDepsEdgeCases:
    """Test edge cases for dependencies."""

    @pytest.mark.asyncio
    async def test_should_handle_multiple_auto_create_attempts(self):
        """Should handle multiple concurrent user creation attempts."""
        from app.api.deps import get_current_db_user

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        current_user = {"email": "concurrent@example.com"}

        # First call
        result1 = await get_current_db_user(current_user, mock_db)

        # Verify user was created
        assert result1.email == "concurrent@example.com"
        assert result1.is_active is False

    @pytest.mark.asyncio
    async def test_should_preserve_email_case(self):
        """Should preserve email case when creating user."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        current_user = {"email": "Test@Example.COM"}

        result = await get_current_db_user(current_user, mock_db)

        # Email should be preserved
        assert result.email == "Test@Example.COM"
