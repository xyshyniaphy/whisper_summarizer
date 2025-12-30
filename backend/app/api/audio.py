"""
音声ファイルAPIエンドポイント
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.supabase import get_current_active_user
from app.models.transcription import Transcription
from app.schemas.transcription import Transcription as TranscriptionSchema
from app.services.whisper_service import whisper_service
from uuid import uuid4
from datetime import datetime
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


def process_audio(file_path: Path, transcription_id: str, db: Session):
    """
    バックグラウンドで音声を処理し、DBを更新する
    """
    logger.info(f"バックグラウンド処理開始: {transcription_id}")
    try:
        # DBからレコードを再取得 (セッションが切れている可能性があるため新しいセッションを使うべきだが、
        # ここでは簡易的に渡されたセッションを使うか、都度作成するか検討。
        # FastAPIのBackgroundTasksではDependency Injectionのセッションはクローズされる可能性がある。
        # そのため、ここではセッションを新しく作るのが正しいが、簡易実装として
        # エラーハンドリング内で処理する。
        # 正しくは BackgroundTasks に db session を渡すべきではない。
        pass
    except Exception as e:
        logger.error(f"バックグラウンド処理準備エラー: {e}")

    # 注: 本番実装ではCeleryなどを使うべきだが、ここでは簡易的に同期実行後にDB更新を行う
    # ただし、Sessionオブジェクトはリクエストスコープで閉じるため、
    # BackgroundTasks内でDB操作をするには新しいセッションが必要。
    # 簡略化のため、今回は「同期的に処理してからレスポンスを返す」か
    # 「メモリ内で処理」するかだが、ユーザー体験向上のためBackgroundTasksを使う。
    # そのため、ここで新しいセッションを作成する。
    from app.db.session import SessionLocal
    background_db = SessionLocal()
    
    try:
        transcription = background_db.query(Transcription).filter(Transcription.id == transcription_id).first()
        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return

        # Whisper実行
        result = whisper_service.transcribe(
            str(file_path),
            output_dir=str(OUTPUT_DIR)
        )
        
        # DB更新
        transcription.original_text = result["text"]
        transcription.language = result["language"]
        transcription.status = "completed"
        # durationはWhisper結果から計算できるなら入れるが、今回は省略
        
        background_db.commit()
        logger.info(f"処理完了: {transcription_id}")
        
    except Exception as e:
        logger.error(f"処理失敗: {transcription_id}, error: {e}")
        if transcription:
            transcription.status = "failed"
            background_db.commit()
    finally:
        background_db.close()


@router.post("/upload", response_model=TranscriptionSchema, status_code=201)
def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    音声ファイルをアップロードして文字起こしを開始
    """
    # ファイル形式のバリデーション
    allowed_extensions = [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"サポートされていないファイル形式です。許可: {', '.join(allowed_extensions)}"
        )
    
    # DBレコード作成
    new_transcription = Transcription(
        file_name=file.filename,
        status="processing",
        user_id=current_user.get("id")
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
            
        # バックグラウンドタスク登録
        background_tasks.add_task(process_audio, file_path, str(new_transcription.id), db)
        
        return new_transcription
        
    except Exception as e:
        logger.error(f"アップロードエラー: {e}")
        db.delete(new_transcription)
        db.commit()
        raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました")
    finally:
        file.file.close()

@router.get("/{audio_id}")
async def get_audio_placeholder():
    # 古いエンドポイントのプレースホルダー
    pass
