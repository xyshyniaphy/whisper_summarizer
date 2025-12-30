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


@router.delete("/{transcription_id}", status_code=204)
async def delete_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    文字起こしを削除 (ファイルも含む)
    """
    transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="文字起こしが見つかりません")

    # ファイル削除
    try:
        import os
        from pathlib import Path
        
        # アップロードファイル削除
        if transcription.file_path and os.path.exists(transcription.file_path):
            os.remove(transcription.file_path)
            
        # 出力ファイル削除 (wav, txt, srt) - 簡易的な推定
        # whisper_service.pyの実装に依存するが、output_dir/id.* を探して消す
        output_dir = Path("/app/data/output")
        for ext in [".wav", ".txt", ".srt", ".vtt", ".json"]:
            output_file = output_dir / f"{transcription.id}{ext}"
            converted_wav = output_dir / f"{transcription.id}_converted.wav"
            
            if output_file.exists():
                output_file.unlink()
            if converted_wav.exists():
                converted_wav.unlink()
                
    except Exception as e:
        logger.error(f"ファイル削除エラー: {e}")
        # DB削除は続行する
        pass

    db.delete(transcription)
    db.commit()
    return None
