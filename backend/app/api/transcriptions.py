"""
文字起こしAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.transcription import Transcription
from app.schemas.transcription import Transcription as TranscriptionSchema

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[TranscriptionSchema])
async def list_transcriptions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    文字起こしリストを取得
    """
    query = db.query(Transcription)
    
    if status:
        query = query.filter(Transcription.status == status)
    
    transcriptions = query.order_by(Transcription.created_at.desc()).offset(offset).limit(limit).all()
    return transcriptions


@router.get("/{transcription_id}", response_model=TranscriptionSchema)
async def get_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    文字起こし詳細を取得
    """
    transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="文字起こしが見つかりません")
    
    return transcription
