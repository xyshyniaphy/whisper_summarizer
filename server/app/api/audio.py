"""
Audio file upload API endpoint for server/runner architecture
Upload creates a pending job that runners will poll and process
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.supabase import get_current_active_user
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.schemas.transcription import Transcription as TranscriptionSchema
from uuid import uuid4
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("/app/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


@router.post("/upload", response_model=TranscriptionSchema, status_code=201)
def upload_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Upload audio file and create pending transcription job.

    The file is saved and a transcription record is created with status="pending".
    Runners will poll for pending jobs and process them automatically.
    """
    # File format validation
    allowed_extensions = [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    # Sync user to local database
    user_id = current_user.get("id")
    user_email = current_user.get("email", "")
    local_user = get_or_create_user(db, user_id, user_email)

    # Create DB record with pending status
    new_transcription = Transcription(
        file_name=file.filename,
        status=TranscriptionStatus.PENDING,
        user_id=local_user.id  # Use local user ID, not Supabase ID
    )
    db.add(new_transcription)
    db.commit()
    db.refresh(new_transcription)

    # Save file
    file_path = UPLOAD_DIR / f"{new_transcription.id}{file_extension}"
    new_transcription.file_path = str(file_path)
    db.commit()

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File uploaded successfully: {file.filename} -> {new_transcription.id} (pending)")
        return new_transcription

    except Exception as e:
        logger.error(f"Upload error: {e}")
        new_transcription.status = TranscriptionStatus.FAILED
        db.commit()
        db.delete(new_transcription)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to save file")
    finally:
        file.file.close()


@router.get("/{audio_id}")
async def get_audio_placeholder():
    # Old endpoint placeholder
    pass
