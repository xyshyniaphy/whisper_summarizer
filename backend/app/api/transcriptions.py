from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from app.api.deps import get_db
from app.core.supabase import get_current_active_user
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.schemas.transcription import Transcription as TranscriptionSchema
from app.schemas.summary import Summary as SummarySchema
from app.services.pptx_service import get_pptx_service

import logging
import asyncio

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


@router.get("/{transcription_id}/download")
async def download_transcription(
  transcription_id: str,
  format: str = Query("txt", pattern="^(txt|srt|pptx)$"),
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_active_user)
):
  """
  下载转录文件
  
  Args:
    transcription_id: 转录ID
    format: 文件格式 (txt, srt 或 pptx)
  
  Returns:
    FileResponse: 下载文件
  """
  # 认证确认
  transcription = db.query(Transcription).filter(
    Transcription.id == transcription_id,
    Transcription.user_id == current_user.get("id")
  ).first()
  
  if not transcription:
    raise HTTPException(status_code=404, detail="未找到转录")
  
  # 构建文件路径
  output_dir = Path("/app/data/output")
  file_path = output_dir / f"{transcription_id}.{format}"
  
  if not file_path.exists():
    raise HTTPException(status_code=404, detail="文件未找到")
  
  # 设置文件名（使用原始文件名）
  original_filename = Path(transcription.file_name).stem
  download_filename = f"{original_filename}.{format}"
  
  # 设置媒体类型
  media_type = "text/plain"
  if format == "pptx":
    media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
  
  return FileResponse(
    path=file_path,
    filename=download_filename,
    media_type=media_type
  )


async def _generate_pptx_task(transcription_id: str, db: Session) -> None:
  """
  后台任务：生成PPTX文件
  
  Args:
    transcription_id: 转录ID
    db: 数据库会话
  """
  try:
    # 获取转录数据
    transcription = db.query(Transcription).filter(
      Transcription.id == transcription_id
    ).first()
    
    if not transcription or not transcription.original_text:
      logger.error(f"转录 {transcription_id} 未找到或没有内容")
      return
    
    # 获取摘要
    summary_text = None
    if transcription.summaries and len(transcription.summaries) > 0:
      summary_text = transcription.summaries[0].summary_text
    
    # 生成PPTX
    pptx_service = get_pptx_service()
    pptx_service.generate_pptx(transcription, summary_text)
    logger.info(f"PPTX生成成功: {transcription_id}.pptx")
    
  except Exception as e:
    logger.error(f"PPTX生成失败 {transcription_id}: {e}")


@router.post("/{transcription_id}/generate-pptx")
async def generate_pptx(
  transcription_id: str,
  background_tasks: BackgroundTasks,
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_active_user)
):
  """
  生成PowerPoint演示文稿
  
  在后台生成包含转录内容和AI摘要的PPTX文件。
  
  Args:
    transcription_id: 转录ID
  
  Returns:
    JSONResponse: 生成状态
  """
  # 验证转录所有权
  transcription = db.query(Transcription).filter(
    Transcription.id == transcription_id,
    Transcription.user_id == current_user.get("id")
  ).first()
  
  if not transcription:
    raise HTTPException(status_code=404, detail="未找到转录")
  
  if not transcription.original_text:
    raise HTTPException(status_code=400, detail="转录内容为空，无法生成PPT")
  
  # 检查文件是否已存在
  pptx_service = get_pptx_service()
  if pptx_service.pptx_exists(transcription_id):
    return JSONResponse(
      status_code=200,
      content={
        "status": "ready",
        "message": "PPTX文件已存在"
      }
    )
  
  # 添加后台任务
  background_tasks.add_task(_generate_pptx_task, transcription_id, db)
  
  return JSONResponse(
    status_code=202,
    content={
      "status": "generating",
      "message": "PPTX生成任务已启动"
    }
  )


@router.get("/{transcription_id}/pptx-status")
async def get_pptx_status(
  transcription_id: str,
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_active_user)
):
  """
  检查PPTX文件是否已生成
  
  Args:
    transcription_id: 转录ID
  
  Returns:
    JSONResponse: PPTX状态
  """
  # 验证转录所有权
  transcription = db.query(Transcription).filter(
    Transcription.id == transcription_id,
    Transcription.user_id == current_user.get("id")
  ).first()
  
  if not transcription:
    raise HTTPException(status_code=404, detail="未找到转录")
  
  pptx_service = get_pptx_service()
  exists = pptx_service.pptx_exists(transcription_id)
  
  return JSONResponse(
    content={
      "status": "ready" if exists else "not_ready",
      "exists": exists
    }
  )
