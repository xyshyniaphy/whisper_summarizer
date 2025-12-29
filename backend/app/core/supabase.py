"""
Supabase認証クライアント
"""

from supabase import create_client, Client
from app.core.config import settings
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
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
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    JWTトークンから現在のユーザーを取得
    
    Args:
        credentials: HTTPベアラートークン
    
    Returns:
        user: ユーザー情報
    
    Raises:
        HTTPException: 認証エラー
    """
    try:
        token = credentials.credentials
        
        # Supabaseでトークンを検証
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )
        
        return user.user
    
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
    # Supabaseの email_confirmed_at をチェック
    if not current_user.get("email_confirmed_at"):
        raise HTTPException(
            status_code=403,
            detail="メールアドレスが確認されていません"
        )
    
    return current_user


async def sign_up(email: str, password: str, full_name: Optional[str] = None) -> dict:
    """
    新規ユーザー登録
    
    Args:
        email: メールアドレス
        password: パスワード
        full_name: フルネーム (オプション)
    
    Returns:
        user: 作成されたユーザー情報
    
    Raises:
        HTTPException: 登録エラー
    """
    try:
        # Supabaseでユーザー作成
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name or ""
                }
            }
        })
        
        if response.user:
            return {
                "user": response.user,
                "session": response.session
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="ユーザー登録に失敗しました"
            )
    
    except Exception as e:
        logger.error(f"サインアップエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"登録エラー: {str(e)}"
        )


async def sign_in(email: str, password: str) -> dict:
    """
    ログイン
    
    Args:
        email: メールアドレス
        password: パスワード
    
    Returns:
        session: セッション情報
    
    Raises:
        HTTPException: ログインエラー
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.session:
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": response.user
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
    
    except Exception as e:
        logger.error(f"サインインエラー: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="ログインに失敗しました"
        )


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
