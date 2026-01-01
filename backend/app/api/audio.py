"""
音声ファイルAPIエンドポイント
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.supabase import get_current_active_user
from app.models.transcription import Transcription
from app.models.user import User
from app.schemas.transcription import Transcription as TranscriptionSchema
from app.services.transcription_processor import TranscriptionProcessor, should_allow_delete
from app.db.session import SessionLocal
from uuid import uuid4
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# アップロードディレクトリ
UPLOAD_DIR = Path("/app/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path("/app/data/output") # Whisper output
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Create processor instance
processor = TranscriptionProcessor(SessionLocal)


def get_or_create_user(db: Session, user_id: str, email: str) -> User:
    """
    Get existing user or create new one in local database.
    Syncs Supabase auth users to local users table.
    """
    # First try to find by ID
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user

    # If not found by ID, check by email and return existing user
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            logger.info(f"Found existing user by email: {email}, using existing ID: {user.id}")
            return user

    # If still not found, create new user
    logger.info(f"Creating new local user record for Supabase user: {user_id}")
    user = User(id=user_id, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def process_audio_task(transcription_id: str):
    """
    バックグラウンドタスクからプロセッサを呼び出す
    """
    logger.info(f"Starting background processing for: {transcription_id}")
    processor.process_transcription(transcription_id)


@router.post("/upload", response_model=TranscriptionSchema, status_code=201)
def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    音声ファイルをアップロードして自動処理を開始（転記→要約）
    """
    # ファイル形式のバリデーション
    allowed_extensions = [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"サポートされていないファイル形式です。許可: {', '.join(allowed_extensions)}"
        )

    # Sync user to local database
    user_id = current_user.get("id")
    user_email = current_user.get("email", "")
    get_or_create_user(db, user_id, user_email)

    # DBレコード作成
    new_transcription = Transcription(
        file_name=file.filename,
        stage="uploading",
        user_id=user_id
    )
    db.add(new_transcription)
    db.commit()
    db.refresh(new_transcription)

    # ファイル保存
    file_path = UPLOAD_DIR / f"{new_transcription.id}{file_extension}"
    new_transcription.file_path = str(file_path)
    db.commit()

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # バックグラウンドタスク登録（自動転記→要約）
        background_tasks.add_task(process_audio_task, str(new_transcription.id))

        logger.info(f"File uploaded successfully: {file.filename} -> {new_transcription.id}")
        return new_transcription

    except Exception as e:
        logger.error(f"アップロードエラー: {e}")
        new_transcription.stage = "failed"
        new_transcription.error_message = f"Upload failed: {str(e)}"
        db.commit()
        db.delete(new_transcription)
        db.commit()
        raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました")
    finally:
        file.file.close()


@router.get("/{audio_id}")
async def get_audio_placeholder():
    # 古いエンドポイントのプレースホルダー
    pass
