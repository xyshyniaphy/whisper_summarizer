from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from app.api.deps import get_db
from app.core.supabase import get_current_active_user
from app.core.gemini import get_gemini_client
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.schemas.transcription import Transcription as TranscriptionSchema
from app.schemas.summary import Summary as SummarySchema

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[TranscriptionSchema])
async def list_transcriptions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    文字起こしリストを取得 (現在のユーザーのもののみ)
    """
    query = db.query(Transcription).filter(Transcription.user_id == current_user.get("id"))
    
    if status:
        query = query.filter(Transcription.status == status)
    
    transcriptions = query.order_by(Transcription.created_at.desc()).offset(offset).limit(limit).all()
    return transcriptions


@router.get("/{transcription_id}", response_model=TranscriptionSchema)
async def get_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    文字起こし詳細を取得
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.get("id")
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="文字起こしが見つかりません")
    
    return transcription


@router.delete("/{transcription_id}", status_code=204)
async def delete_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    文字起こしを削除 (ファイルも含む)
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.get("id")
    ).first()
    
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


@router.post("/{transcription_id}/summarize", response_model=SummarySchema)
async def generate_summary(
  transcription_id: str,
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_active_user)
):
  """
  文字起こしから要約を生成
  """
  # 文字起こしを取得
  transcription = db.query(Transcription).filter(
    Transcription.id == transcription_id,
    Transcription.user_id == current_user.get("id")
  ).first()
  
  if not transcription:
    raise HTTPException(status_code=404, detail="文字起こしが見つかりません")
  
  if not transcription.original_text:
    raise HTTPException(status_code=400, detail="文字起こしテキストがありません")
  
  # 既に要約が存在するか確認
  existing_summary = db.query(Summary).filter(
    Summary.transcription_id == transcription_id
  ).first()
  
  if existing_summary:
    return existing_summary
  
  try:
    # Geminiで要約生成
    gemini_client = get_gemini_client()
    summary_text = await gemini_client.generate_summary(transcription.original_text)
    
    # Summaryを保存
    new_summary = Summary(
      transcription_id=transcription_id,
      summary_text=summary_text,
      model_name=gemini_client.model
    )
    db.add(new_summary)
    db.commit()
    db.refresh(new_summary)
    
    logger.info(f"要約生成完了: {transcription_id}")
    return new_summary
  
  except Exception as e:
    logger.error(f"要約生成エラー: {transcription_id}, error: {e}")
    raise HTTPException(status_code=500, detail=f"要約生成に失敗しました: {str(e)}")


@router.get("/{transcription_id}/download")
async def download_transcription(
  transcription_id: str,
  format: str = Query("txt", pattern="^(txt|srt)$"),
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_active_user)
):
  """
  文字起こしファイルをダウンロード
  
  Args:
    transcription_id: 文字起こしID
    format: ファイル形式 (txt または srt)
  
  Returns:
    FileResponse: ダウンロードファイル
  """
  # 認証確認
  transcription = db.query(Transcription).filter(
    Transcription.id == transcription_id,
    Transcription.user_id == current_user.get("id")
  ).first()
  
  if not transcription:
    raise HTTPException(status_code=404, detail="文字起こしが見つかりません")
  
  # ファイルパスを構築
  output_dir = Path("/app/data/output")
  file_path = output_dir / f"{transcription_id}.{format}"
  
  if not file_path.exists():
    raise HTTPException(status_code=404, detail="ファイルが見つかりません")
  
  # ファイル名を設定（元のファイル名を使用）
  original_filename = Path(transcription.file_name).stem
  download_filename = f"{original_filename}.{format}"
  
  return FileResponse(
    path=file_path,
    filename=download_filename,
    media_type="text/plain"
  )
