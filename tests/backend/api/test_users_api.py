"""
Users API エンドポイントテスト

ユーザー情報の取得、更新機能を検証する。
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestUsersAPI:
    """Users API 統合テスト"""

    def test_get_me_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで /users/me にアクセスするとエラーになるテスト"""
        response = test_client.get("/api/users/me")
        assert response.status_code in [401, 403]

    def test_get_me_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """認証済みで /users/me が成功するテスト"""
        response = real_auth_client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == real_auth_user["id"]
        assert "email" in data

    def test_update_me_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで更新するとエラーになるテスト"""
        response = test_client.put("/api/users/me", json={"full_name": "Test"})
        assert response.status_code in [401, 403]

    def test_update_me_success(self, real_auth_client: TestClient) -> None:
        """ユーザー情報の更新が成功するテスト"""
        update_data = {
            "full_name": "Updated Name"
        }
        response = real_auth_client.put("/api/users/me", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_update_me_with_invalid_data(self, real_auth_client: TestClient) -> None:
        """無効なデータで更新するとエラーになるテスト"""
        # 無効なメールアドレス形式
        response = real_auth_client.put("/api/users/me", json={"email": "invalid-email"})
        assert response.status_code == 422

    def test_get_me_with_expired_token(self, test_client: TestClient) -> None:
        """期限切れトークンでアクセスするとエラーになるテスト"""
        # 無効なトークンをヘッダーに設定
        response = test_client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 403]
