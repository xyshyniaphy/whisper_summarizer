"""
Supabase認証クライアント

Google OAuthのみをサポートしています。
"""

from supabase import create_client, Client
from app.core.config import settings
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
from datetime import datetime
import logging

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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    JWTトークンから現在のユーザーを取得 (Google OAuth)

    Args:
        credentials: HTTPベアラートークン

    Returns:
        user: ユーザー情報 (dict)

    Raises:
        HTTPException: 認証エラー
    """
    # Bypass auth if DISABLE_AUTH is set (for testing)
    if settings.DISABLE_AUTH:
        return {
            "id": UUID("123e4567-e89b-42d3-a456-426614174000"),  # UUID object for SQLAlchemy
            "email": "test@example.com",
            "email_confirmed_at": datetime.utcnow(),
            "phone": None,
            "last_sign_in_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "user_metadata": {"role": "admin"},
            "app_metadata": {},
        }

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
        return {
            "id": str(user.user.id),
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
