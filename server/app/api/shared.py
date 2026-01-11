"""
Shared Transcription API Router

Public access endpoints for shared transcriptions (no authentication required).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
from app.api.deps import get_db
from app.models.transcription import Transcription
from app.models.share_link import ShareLink
from app.schemas.share import (
    SharedTranscriptionResponse,
    SharedChatRequest,
    SharedChatResponse
)
from app.core.rate_limit import rate_limit_shared_chat
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


@router.post("/{share_token}/chat", response_model=SharedChatResponse)
async def send_shared_chat_message(
    share_token: str,
    message: SharedChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    通过分享链接发送AI聊天消息（无需认证）
    
    Features:
    - No authentication required
    - Uses transcription as context
    - No chat history (stateless)
    - Rate limited per IP (10 req/min)
    - No message persistence for anonymous users
    
    Args:
        share_token: Share token from the share link
        message: Chat message with content field
        request: FastAPI Request object (for IP extraction)
        db: Database session
        
    Returns:
        AI assistant response
        
    Raises:
        404: Share link not found or transcription not found
        400: Empty message content
        410: Share link expired
        429: Rate limit exceeded
        500: Internal server error
    """
    client_ip = request.client.host or "unknown"
    
    # Rate limiting (IP-based)
    if not rate_limit_shared_chat(client_ip):
        logger.warning(f"[SharedChat] Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试"
        )
    
    # Validate share token
    share_link = db.query(ShareLink).filter(
        ShareLink.share_token == share_token
    ).first()
    
    if not share_link:
        logger.info(f"[SharedChat] Invalid share token: {share_token}")
        raise HTTPException(status_code=404, detail="分享链接不存在")
    
    # Check expiration
    from datetime import datetime, timezone
    if share_link.expires_at and share_link.expires_at < datetime.now(timezone.utc):
        logger.info(f"[SharedChat] Expired share token: {share_token}")
        raise HTTPException(status_code=410, detail="分享链接已过期")
    
    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == share_link.transcription_id
    ).first()
    
    if not transcription:
        logger.error(f"[SharedChat] Transcription not found: {share_link.transcription_id}")
        raise HTTPException(status_code=404, detail="转录不存在")
    
    user_content = message.content.strip()
    if not user_content:
        logger.warning("[SharedChat] Empty content received")
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    logger.info(f"[SharedChat] Processing message for share: {share_token}, content: {user_content[:100]}...")
    
    # Get transcription text for context
    transcription_text = transcription.text
    logger.info(f"[SharedChat] Transcription text length: {len(transcription_text)} chars")
    
    # Call GLM API (stateless - no chat history for anonymous users)
    try:
        from app.core.glm import get_glm_client
        glm_client = get_glm_client()
        
        logger.info("[SharedChat] Calling GLM API...")
        response = await glm_client.chat(
            question=user_content,
            transcription_context=transcription_text,
            chat_history=[]  # No history for anonymous users (stateless)
        )
        
        assistant_content = response.get("response", "")
        logger.info(f"[SharedChat] GLM response received, length: {len(assistant_content)} chars")
        
    except Exception as e:
        logger.error(f"[SharedChat] GLM chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="抱歉，AI回复失败，请稍后再试"
        )
    
    # Return response (no persistence for anonymous users)
    return SharedChatResponse(
        role="assistant",
        content=assistant_content
    )
