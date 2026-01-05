"""
ユーザーAPIエンドポイント
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import UserResponse
from app.api.deps import get_db, get_current_db_user, require_active
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me")
async def get_me(
    current_db_user: User = Depends(require_active)
):
    """
    現在のユーザー情報を取得

    Returns user info from local database including activation status.
    """
    # Combine Supabase auth data with local database data
    return {
        "id": str(current_db_user.id),
        "email": current_db_user.email,
        "is_active": current_db_user.is_active,
        "is_admin": current_db_user.is_admin,
        "activated_at": current_db_user.activated_at,
        "created_at": current_db_user.created_at
    }


@router.put("/me")
async def update_me(
    full_name: str,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(require_active)
):
    """
    ユーザー情報を更新 (currently a placeholder)

    Note: Full name is stored in Supabase Auth, not local database.
    This endpoint is reserved for future use.
    """
    # TODO: Update user metadata in Supabase if needed
    return {"message": "ユーザー情報を更新しました"}
