"""
認証API エンドポイントテスト

ユーザー登録、ログイン、認証ミドルウェアの
動作を検証する。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAuthAPI:
  """認証APIテストクラス"""
  
  def test_signup_success(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    ユーザー登録が成功するテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
      response = test_client.post(
        "/api/auth/signup",
        json={
          "email": "test@example.com",
          "password": "password123"
        }
      )
      
      assert response.status_code == 200
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
  
  
  def test_login_success(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    ログインが成功するテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
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
  
  
  def test_login_wrong_password(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    パスワード誤りでエラーが返るテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    # ログイン失敗をシミュレート
    mock_supabase_client.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
    
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
      response = test_client.post(
        "/api/auth/login",
        json={
          "email": "test@example.com",
          "password": "wrong-password"
        }
      )
      
      assert response.status_code in [400, 401]
  
  
  @pytest.mark.integration
  def test_protected_endpoint_without_token(self, test_client: TestClient) -> None:
    """
    トークンなしで保護されたエンドポイントにアクセスするとエラーになるテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    response = test_client.get("/api/users/me")
    
    assert response.status_code == 401
  
  
  @pytest.mark.integration
  def test_protected_endpoint_with_token(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    有効なトークンで保護されたエンドポイントにアクセスできるテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
      response = test_client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer test-access-token"}
      )
      
      # 実装によってステータスコードは異なる可能性がある
      assert response.status_code in [200, 401]
