"""
文字起こしAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.schemas import TranscriptionResponse, TranscriptionListResponse
from app.core.supabase import get_current_active_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TranscriptionListResponse)
async def list_transcriptions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    文字起こしリストを取得
    
    Args:
        limit: 取得件数 (1-100)
        offset: オフセット
        status: ステータスフィルター (completed, processing, failed)
        current_user: 認証されたユーザー
    
    Returns:
        TranscriptionListResponse: 文字起こしリスト
    """
    # TODO: データベースから取得
    return TranscriptionListResponse(
        total=0,
        items=[],
        limit=limit,
        offset=offset
    )


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    文字起こし詳細を取得
    
    Args:
        transcription_id: 文字起こしID
        current_user: 認証されたユーザー
    
    Returns:
        TranscriptionResponse: 文字起こし情報
    """
    # TODO: データベースから取得
    raise HTTPException(status_code=501, detail="未実装")
