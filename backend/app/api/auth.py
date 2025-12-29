"""
認証APIエンドポイント
"""

from fastapi import APIRouter, HTTPException
from app.schemas.schemas import SignUpRequest, SignInRequest, AuthResponse
from app.core.supabase import sign_up, sign_in, sign_out
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(request: SignUpRequest):
    """
    新規ユーザー登録
    
    Args:
        request: サインアップリクエスト (email, password, full_name)
    
    Returns:
        AuthResponse: アクセストークンとユーザー情報
    """
    try:
        result = await sign_up(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        return AuthResponse(
            access_token=result["session"].access_token if result.get("session") else "",
            refresh_token=result["session"].refresh_token if result.get("session") else None,
            user=result["user"].__dict__
        )
    
    except Exception as e:
        logger.error(f"サインアップエラー: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(request: SignInRequest):
    """
    ログイン
    
    Args:
        request: サインインリクエスト (email, password)
    
    Returns:
        AuthResponse: アクセストークンとユーザー情報
    """
    try:
        result = await sign_in(
            email=request.email,
            password=request.password
        )
        
        return AuthResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            user=result["user"].__dict__
        )
    
    except Exception as e:
        logger.error(f"ログインエラー: {str(e)}")
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")


@router.post("/logout")
async def logout():
    """
    ログアウト
    
    Returns:
        message: ログアウトメッセージ
    """
    try:
        result = await sign_out("")
        return result
    
    except Exception as e:
        logger.error(f"ログアウトエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="ログアウトに失敗しました")
