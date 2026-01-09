"""
Shared Transcription API Router

Public access endpoints for shared transcriptions (no authentication required).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.api.deps import get_db
from app.models.transcription import Transcription
from app.models.share_link import ShareLink
from app.schemas.share import SharedTranscriptionResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{share_token}", response_model=SharedTranscriptionResponse)
async def get_shared_transcription(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    访问公开分享的转录（无需认证）
    """
    # Find share link
    share_link = db.query(ShareLink).filter(
        ShareLink.share_token == share_token
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    # Check expiration
    if share_link.expires_at and share_link.expires_at < __import__('datetime').datetime.now(__import__('datetime').timezone.utc):
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # Increment access count
    share_link.access_count += 1
    db.commit()

    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == share_link.transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="转录不存在")

    # Get summary
    summary = None
    if transcription.summaries and len(transcription.summaries) > 0:
        summary = transcription.summaries[0].summary_text

    return SharedTranscriptionResponse(
        id=transcription.id,
        file_name=transcription.file_name,
        text=transcription.text,
        summary=summary,
        language=transcription.language,
        duration_seconds=transcription.duration_seconds,
        created_at=transcription.created_at
    )
