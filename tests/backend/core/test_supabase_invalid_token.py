"""
Supabase Invalid Token Tests

Tests for supabase.py line 77 - invalid token handling.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.supabase import get_current_user


@pytest.fixture
def mock_credentials():
    """Mock HTTP bearer credentials."""
    creds = Mock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "invalid-test-token"
    return creds


@pytest.mark.asyncio
class TestSupabaseInvalidToken:
    """Test supabase invalid token handling."""

    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_invalid_token_returns_none_hits_line_77(
        self,
        mock_supabase,
        mock_settings,
        mock_credentials
    ) -> None:
        """
        Test that invalid token causes get_user to return None, triggering line 77.

        This targets supabase.py line 77:
        ```python
        if not user:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )
        ```

        Scenario:
        1. Mock supabase.auth.get_user to return None
        2. Call get_current_user with invalid token
        3. Should hit line 77 (user is None check) and raise HTTPException
        """
        mock_settings.DISABLE_AUTH = False

        # Mock get_user to return None (invalid token scenario)
        # This triggers line 76: user = supabase.auth.get_user(token)
        # Then line 77 check: if not user: raise HTTPException
        mock_supabase.auth.get_user.return_value = None

        # Calling get_current_user should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials)

        # Verify it's a 401 error
        assert exc_info.value.status_code == 401

        # Note: The except block (lines 95-99) catches the HTTPException
        # from line 77 and re-raises with a generic error message
        # Line 96 logs: "認証エラー: 401: 無効なトークンです"
        assert exc_info.value.detail == "認証に失敗しました"

        # Verify get_user was called with the token
        mock_supabase.auth.get_user.assert_called_once_with("invalid-test-token")

    @patch('app.core.supabase.settings')
    @patch('app.core.supabase.supabase')
    async def test_none_user_object_hits_line_77(
        self,
        mock_supabase,
        mock_settings,
        mock_credentials
    ) -> None:
        """
        Test that None user object triggers line 77.

        This specifically tests the case where supabase returns None
        instead of a user object, which should trigger line 77.

        Note: The except block (lines 95-99) catches the HTTPException
        from line 77 and re-raises with a generic error message.

        Scenario:
        1. Mock supabase.auth.get_user to return None explicitly
        2. Verify line 77 is executed (HTTPException raised)
        3. Verify the except block catches it (line 96 logs the error)
        """
        mock_settings.DISABLE_AUTH = False

        # Explicitly return None from get_user
        mock_supabase.auth.get_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials)

        # Line 77 raises HTTPException with "無効なトークンです"
        # But lines 95-99 catch it and re-raise with "認証に失敗しました"
        assert exc_info.value.status_code == 401

        # The final error message is from the except block (line 99)
        # not from line 77 directly
        assert exc_info.value.detail == "認証に失敗しました"
