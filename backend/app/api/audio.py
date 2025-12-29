"""
音声ファイルAPIエンドポイント
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from app.schemas.schemas import AudioUploadResponse, AudioFileResponse
from app.core.supabase import get_current_active_user
from app.core.config import settings
from uuid import uuid4
from datetime import datetime
import httpx
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# アップロードディレクトリ
UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=AudioUploadResponse, status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """
    音声ファイルをアップロードして文字起こしを開始
    
    Args:
        file: 音声ファイル (m4a, mp3, wav, aac, flac, ogg)
        current_user: 認証されたユーザー
    
    Returns:
        AudioUploadResponse: アップロード結果
    """
    # ファイル形式のバリデーション
    allowed_extensions = [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"サポートされていないファイル形式です。許可: {', '.join(allowed_extensions)}"
        )
    
    # 一意のファイルIDを生成
    file_id = uuid4()
    file_path = UPLOAD_DIR / f"{file_id}{file_extension}"
    
    try:
        # ファイルを保存
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"音声ファイルをアップロードしました: {file.filename} ({file_size} bytes)")
        
        # Whisper.cppで文字起こしを実行
        # TODO: バックグラウンドタスクで実行
        try:
            from app.services.whisper_service import whisper_service
            
            transcription_data = await whisper_service.transcribe(
                str(file_path),
                output_dir="/app/output"
            )
            
            logger.info(f"文字起こしが完了しました: {file.filename}")
            logger.info(f"文字数: {len(transcription_data['text'])}")
            
            # TODO: データベースに保存
            # TODO: GLM4.7で要約を生成
        
        except Exception as e:
            logger.error(f"Whisper.cpp実行エラー: {str(e)}")
        
        # レスポンスを返す
        return AudioUploadResponse(
            id=file_id,
            filename=file.filename,
            file_size=file_size,
            status="processing",
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"ファイルアップロードエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="ファイルのアップロードに失敗しました"
        )
    
    finally:
        file.file.close()


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio(
    audio_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    音声ファイルの詳細を取得
    
    Args:
        audio_id: 音声ファイルID
        current_user: 認証されたユーザー
    
    Returns:
        AudioFileResponse: 音声ファイル情報
    """
    # TODO: データベースから取得
    raise HTTPException(status_code=501, detail="未実装")
