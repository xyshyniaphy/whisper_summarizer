"""
Supabase Core Tests

Tests for Supabase authentication and user management functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.supabase import get_current_user, get_current_active_user, sign_out


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_credentials():
    """Mock HTTP bearer credentials."""
    creds = Mock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "valid-test-token"
    return creds


@pytest.fixture
def mock_supabase_user():
    """Mock Supabase user object."""
    user = Mock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.email_confirmed_at = datetime.now(timezone.utc)
    user.phone = None
    user.last_sign_in_at = datetime.now(timezone.utc)
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.user_metadata = {"name": "Test User"}
    user.app_metadata = {"provider": "google"}
    return user


# ============================================================================
# get_current_user() Tests
# ============================================================================

class TestGetCurrentUser:
    """Test get_current_user function."""

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    async def test_should_return_test_user_when_auth_disabled(self, mock_settings):
        """Should return test user when DISABLE_AUTH is enabled."""
        mock_settings.DISABLE_AUTH = True

        result = await get_current_user(credentials=None)

        assert result is not None
        assert result["email"] == "test@example.com"
        assert isinstance(result["id"], UUID)

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_return_user_with_valid_token(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should return user with valid token."""
        mock_settings.DISABLE_AUTH = False
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["email"] == "test@example.com"
        assert result["email_confirmed_at"] is not None
        assert "id" in result
        mock_supabase.auth.get_user.assert_called_once_with("valid-test-token")

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    async def test_should_raise_401_without_credentials(self, mock_settings):
        """Should raise 401 when no credentials provided."""
        mock_settings.DISABLE_AUTH = False

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)

        assert exc_info.value.status_code == 401
        assert "認証が必要です" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_raise_401_with_invalid_token(self, mock_supabase, mock_settings, mock_credentials):
        """Should raise 401 with invalid token (None is truthy check fails)."""
        mock_settings.DISABLE_AUTH = False
        # When get_user returns None, the "if not user" check triggers
        # but the actual code might throw an exception when accessing user.user
        mock_supabase.auth.get_user.side_effect = AttributeError("'NoneType' object has no attribute 'user'")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_handle_auth_exception(self, mock_supabase, mock_settings, mock_credentials):
        """Should handle authentication exceptions."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase.auth.get_user.side_effect = Exception("Auth failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "認証に失敗しました" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_convert_user_to_dict(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should convert User object to dict correctly."""
        mock_settings.DISABLE_AUTH = False
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert isinstance(result, dict)
        assert "id" in result
        assert "email" in result
        assert "user_metadata" in result
        assert "app_metadata" in result
        assert result["user_metadata"]["name"] == "Test User"


# ============================================================================
# get_current_active_user() Tests
# ============================================================================

class TestGetCurrentActiveUser:
    """Test get_current_active_user function."""

    @pytest.mark.asyncio
    async def test_should_return_user_with_confirmed_email(self):
        """Should return user when email is confirmed."""
        current_user = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "email_confirmed_at": datetime.now(timezone.utc),
            "user_metadata": {},
        }

        result = await get_current_active_user(current_user)

        assert result == current_user

    @pytest.mark.asyncio
    async def test_should_raise_403_without_confirmed_email(self):
        """Should raise 403 when email not confirmed."""
        current_user = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "email_confirmed_at": None,
            "user_metadata": {},
        }

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user)

        assert exc_info.value.status_code == 403
        assert "メールアドレスが確認されていません" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_should_raise_403_with_missing_email_confirmed_field(self):
        """Should raise 403 when email_confirmed_at field is missing."""
        current_user = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "user_metadata": {},
        }

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user)

        assert exc_info.value.status_code == 403


# ============================================================================
# sign_out() Tests
# ============================================================================

class TestSignOut:
    """Test sign_out function."""

    @pytest.mark.asyncio
    @patch('app.core.supabase.supabase')
    async def test_should_sign_out_successfully(self, mock_supabase):
        """Should sign out successfully."""
        mock_supabase.auth.sign_out.return_value = None

        result = await sign_out("test-token")

        assert result["message"] == "ログアウトしました"
        mock_supabase.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.core.supabase.supabase')
    async def test_should_handle_sign_out_exception(self, mock_supabase):
        """Should handle sign out exceptions."""
        mock_supabase.auth.sign_out.side_effect = Exception("Sign out failed")

        with pytest.raises(HTTPException) as exc_info:
            await sign_out("test-token")

        assert exc_info.value.status_code == 500
        assert "ログアウトに失敗しました" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('app.core.supabase.supabase')
    async def test_should_handle_sign_out_with_empty_token(self, mock_supabase):
        """Should handle empty token."""
        mock_supabase.auth.sign_out.return_value = None

        result = await sign_out("")

        assert result is not None

    @pytest.mark.asyncio
    @patch('app.core.supabase.supabase')
    async def test_should_handle_connection_error(self, mock_supabase):
        """Should handle connection errors."""
        mock_supabase.auth.sign_out.side_effect = ConnectionError("Network error")

        with pytest.raises(HTTPException) as exc_info:
            await sign_out("test-token")

        assert exc_info.value.status_code == 500


# ============================================================================
# User Metadata Tests
# ============================================================================

class TestUserMetadata:
    """Test user metadata handling."""

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_include_user_metadata_in_response(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should include user_metadata in response."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase_user.user_metadata = {"name": "Test User", "avatar": "avatar.png"}
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["user_metadata"]["name"] == "Test User"
        assert result["user_metadata"]["avatar"] == "avatar.png"

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_include_app_metadata_in_response(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should include app_metadata in response."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase_user.app_metadata = {"provider": "google", "role": "user"}
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["app_metadata"]["provider"] == "google"
        assert result["app_metadata"]["role"] == "user"


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_handle_user_with_none_email(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should handle user with None email."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase_user.email = None
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["email"] is None

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_handle_user_with_empty_metadata(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should handle user with empty metadata."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase_user.user_metadata = {}
        mock_supabase_user.app_metadata = {}
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["user_metadata"] == {}
        assert result["app_metadata"] == {}

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    async def test_should_return_uuid_as_string_when_auth_disabled(self, mock_settings):
        """When auth is disabled, ID should be UUID object for SQLAlchemy."""
        mock_settings.DISABLE_AUTH = True

        result = await get_current_user(credentials=None)

        # Test user has UUID object (for SQLAlchemy)
        assert isinstance(result["id"], UUID)


# ============================================================================
# Timestamp Tests
# ============================================================================

class TestTimestamps:
    """Test timestamp handling."""

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_preserve_timestamps(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should preserve user timestamps."""
        mock_settings.DISABLE_AUTH = False
        now = datetime.now(timezone.utc)
        mock_supabase_user.created_at = now
        mock_supabase_user.updated_at = now
        mock_supabase_user.last_sign_in_at = now
        mock_supabase_user.email_confirmed_at = now
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["created_at"] == now
        assert result["updated_at"] == now
        assert result["last_sign_in_at"] == now
        assert result["email_confirmed_at"] == now

    @pytest.mark.asyncio
    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_should_handle_none_timestamps(self, mock_supabase, mock_settings, mock_credentials, mock_supabase_user):
        """Should handle None timestamps."""
        mock_settings.DISABLE_AUTH = False
        mock_supabase_user.last_sign_in_at = None
        mock_supabase_user.phone = None
        mock_user_obj = Mock()
        mock_user_obj.user = mock_supabase_user
        mock_supabase.auth.get_user.return_value = mock_user_obj

        result = await get_current_user(mock_credentials)

        assert result["last_sign_in_at"] is None
        assert result["phone"] is None
