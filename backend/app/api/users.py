"""
ユーザーAPIエンドポイント
"""

from fastapi import APIRouter, Depends
from app.schemas.schemas import UserResponse
from app.core.supabase import get_current_active_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_active_user)):
    """
    現在のユーザー情報を取得
    
    Args:
        current_user: 認証されたユーザー
    
    Returns:
        UserResponse: ユーザー情報
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("user_metadata", {}).get("full_name"),
        email_confirmed_at=current_user.get("email_confirmed_at"),
        created_at=current_user["created_at"]
    )


@router.put("/me")
async def update_me(
    full_name: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    ユーザー情報を更新
    
    Args:
        full_name: フルネーム
        current_user: 認証されたユーザー
    
    Returns:
        message: 更新メッセージ
    """
    # TODO: Supabase Auth APIでユーザー情報を更新
    return {"message": "ユーザー情報を更新しました"}
