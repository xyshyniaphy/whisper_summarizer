"""
認証APIエンドポイント

Google OAuthのみをサポートしています。
メール/パスワードでのログイン・登録は廃止されました。
"""

from fastapi import APIRouter, HTTPException
from app.core.supabase import sign_out
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
