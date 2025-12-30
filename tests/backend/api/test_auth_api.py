"""
認証API エンドポイントテスト

ユーザー登録、ログイン、認証ミドルウェアの
動作を検証する。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.schemas import AuthResponse
from app.main import app
from types import SimpleNamespace


class TestAuthAPI:
  """認証APIのテスト"""
  
  @pytest.mark.integration
  def test_signup_success(self, test_client: TestClient) -> None:
    """
    ユーザー登録成功のテスト
    """
    mock_user = SimpleNamespace(
        id="test-user-id",
        email="test@example.com",
        created_at="2025-01-01"
    )
    mock_session = SimpleNamespace(
        access_token="test-access-token",
        refresh_token="test-refresh-token"
    )
    
    with patch("app.api.auth.sign_up", new_callable=AsyncMock) as mock_sign_up:
      mock_sign_up.return_value = {
        "user": mock_user,
        "session": mock_session
      }
      response = test_client.post(
        "/api/auth/signup",
        json={
          "email": "test@example.com",
          "password": "password123"
        }
      )
      
      assert response.status_code == 201
      data = response.json()
      assert "user" in data
      assert data["user"]["email"] == "test@example.com"
  
  
  def test_signup_invalid_email(self, test_client: TestClient) -> None:
    """
    無効なメールアドレスでエラーが返るテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    response = test_client.post(
      "/api/auth/signup",
      json={
        "email": "invalid-email",
        "password": "password123"
      }
    )
    
    assert response.status_code == 422
  
  
  def test_login_success(self, test_client: TestClient) -> None:
    """
    ログインが成功するテスト
    """
    mock_user = SimpleNamespace(
        id="test-user-id",
        email="test@example.com",
        created_at="2025-01-01"
    )
    
    with patch("app.api.auth.sign_in", new_callable=AsyncMock) as mock_sign_in:
      mock_sign_in.return_value = {
        "user": mock_user,
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token"
      }
      response = test_client.post(
        "/api/auth/login",
        json={
          "email": "test@example.com",
          "password": "password123"
        }
      )
      
      assert response.status_code == 200
      data = response.json()
      assert "access_token" in data
  
  
  def test_login_wrong_password(self, test_client: TestClient) -> None:
    """
    パスワード誤りでエラーが返るテスト
    """
    with patch("app.api.auth.sign_in", new_callable=AsyncMock) as mock_sign_in:
      mock_sign_in.side_effect = Exception("Invalid credentials")
      response = test_client.post(
        "/api/auth/login",
        json={
          "email": "test@example.com",
          "password": "wrong-password"
        }
      )
      
      assert response.status_code in [401, 403]
  
  
  @pytest.mark.integration
  def test_protected_endpoint_without_token(self, test_client: TestClient) -> None:
    """
    トークンなしで保護されたエンドポイントにアクセスできないテスト
    """
    response = test_client.get("/api/users/me")
    
    assert response.status_code in [401, 403]
  
  
  @pytest.mark.integration
  def test_protected_endpoint_with_token(self, test_client: TestClient) -> None:
    """
    有効なトークンで保護されたエンドポイントにアクセスできるテスト
    """
    from app.core.supabase import get_current_active_user
    mock_user = {
        "id": "bae0bdba-80ae-4354-8339-ab3d81259762", 
        "email": "test@example.com", 
        "created_at": "2025-01-01",
        "email_confirmed_at": "2025-01-01",
        "user_metadata": {"full_name": "Test User"}
    }
    
    async def override_get_user():
        return mock_user
        
    app.dependency_overrides[get_current_active_user] = override_get_user
    try:
        response = test_client.get(
          "/api/users/me",
          headers={"Authorization": "Bearer test-access-token"}
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides = {}
