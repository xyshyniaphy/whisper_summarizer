"""
Supabase認証クライアント

Google OAuthのみをサポートしています。

Localhostリクエストは認証をバイパスしてテストユーザーを使用します
（デバッグおよび自動テスト用）。
"""

from supabase import create_client, Client
from app.core.config import settings
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

# Import auth bypass for localhost testing
from app.core.auth_bypass import (
    is_localhost_request,
    get_test_user,
    log_bypassed_request
)

logger = logging.getLogger(__name__)

# Supabaseクライアントの初期化
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

# サービスロールクライアント (管理者操作用)
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

# HTTPベアラートークン認証
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    JWTトークンから現在のユーザーを取得 (Google OAuth)

    Localhostリクエスト（127.0.0.1）の場合、認証をバイパスして
    テストユーザーを返します（デバッグおよび自動テスト用）。

    Args:
        request: FastAPI Requestオブジェクト
        credentials: HTTPベアラートークン

    Returns:
        user: ユーザー情報 (dict)

    Raises:
        HTTPException: 認証エラー
    """
    # Localhost bypass - HARDCODED for testing/debugging
    # セキュリティ: 環境変数ではなくIPアドレスでハードコードされているため、
    # 本番環境での誤設定を防ぎます
    if is_localhost_request(request):
        test_user = get_test_user()
        log_bypassed_request(request, test_user)
        return test_user

    # Check if credentials provided
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="認証が必要です"
        )

    try:
        token = credentials.credentials

        # Supabaseでトークンを検証
        user = supabase.auth.get_user(token)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )

        # Convert User object to dict
        # UUID文字列をUUIDオブジェクトに変換（SQLAlchemy用）
        return {
            "id": UUID(str(user.user.id)),
            "email": user.user.email,
            "email_confirmed_at": user.user.email_confirmed_at,
            "phone": user.user.phone,
            "last_sign_in_at": user.user.last_sign_in_at,
            "created_at": user.user.created_at,
            "updated_at": user.user.updated_at,
            "user_metadata": user.user.user_metadata,
            "app_metadata": user.user.app_metadata,
        }

    except Exception as e:
        logger.error(f"認証エラー: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="認証に失敗しました"
        )


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    アクティブなユーザーのみを許可

    Args:
        current_user: 現在のユーザー

    Returns:
        user: ユーザー情報

    Raises:
        HTTPException: ユーザーが無効
    """
    # Supabaseの email_confirmed_at をチェック (Google OAuthは自動確認)
    if not current_user.get("email_confirmed_at"):
        raise HTTPException(
            status_code=403,
            detail="メールアドレスが確認されていません"
        )

    return current_user


async def sign_out(token: str) -> dict:
    """
    ログアウト

    Args:
        token: アクセストークン

    Returns:
        result: ログアウト結果
    """
    try:
        supabase.auth.sign_out()
        return {"message": "ログアウトしました"}

    except Exception as e:
        logger.error(f"サインアウトエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="ログアウトに失敗しました"
        )
