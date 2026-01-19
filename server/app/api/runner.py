"""
Runner API endpoints - for job queue management

These endpoints are used by GPU runners to poll for jobs, claim them,
download audio, and submit results.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import os
import logging

from app.db.session import get_db
from app.models.transcription import Transcription, TranscriptionStatus
from app.schemas.runner import (
    JobResponse, JobListResponse,
    JobCompleteRequest, JobStartRequest,
    AudioDownloadResponse, HeartbeatRequest, HeartbeatResponse
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# API key for runner authentication
RUNNER_API_KEY = os.getenv("RUNNER_API_KEY", "dev-secret-key")


async def verify_runner(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify runner API key."""
    if credentials.credentials != RUNNER_API_KEY:
        logger.warning(f"Failed runner auth attempt with key: {credentials.credentials[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid runner API key"
        )
    return credentials.credentials


@router.get("/jobs", response_model=List[JobResponse])
async def get_pending_jobs(
    status_filter: str = "pending",
    limit: int = 10,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Get pending transcription jobs for runners to process.

    Args:
        status_filter: Filter by status (default: pending)
        limit: Maximum number of jobs to return
        db: Database session
        api_key: Verified runner API key

    Returns:
        List of pending jobs
    """
    # Validate status filter
    valid_statuses = ["pending", "processing", "completed", "failed"]
    if status_filter not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    jobs = db.query(Transcription)\
        .filter(Transcription.status == status_filter)\
        .order_by(Transcription.created_at)\
        .limit(limit)\
        .all()

    logger.info(f"Returning {len(jobs)} jobs with status '{status_filter}'")
    return [
        JobResponse(
            id=str(job.id),
            file_name=job.file_name,
            file_path=job.file_path,
            storage_path=job.storage_path,
            language=job.language,
            created_at=job.created_at
        )
        for job in jobs
    ]


@router.post("/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    request: JobStartRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Mark a job as started (claimed by a runner).

    Args:
        job_id: UUID of the transcription job
        request: Start request with runner_id
        db: Database session
        api_key: Verified runner API key

    Returns:
        Success status
    """
    from app.db.base_class import Base
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(Transcription).filter(Transcription.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != TranscriptionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Job not available (current status: {job.status})"
        )

    job.status = TranscriptionStatus.PROCESSING
    job.runner_id = request.runner_id
    job.started_at = datetime.now(timezone.utc)

    db.commit()
    logger.info(f"Job {job_id} started by runner {request.runner_id}")
    return {"status": "started", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: str,
    result: JobCompleteRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Submit transcription result and mark job as completed.

    This endpoint:
    1. Saves the transcription text and summary
    2. Marks job as completed
    3. Deletes the audio file to save disk space
    4. Records processing time

    Args:
        job_id: UUID of the transcription job
        result: Completion result with text and summary
        db: Database session
        api_key: Verified runner API key

    Returns:
        Success status
    """
    from datetime import datetime, timezone
    from app.db.base_class import Base
    import uuid
    import os
    from app.services.storage_service import get_storage_service

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(Transcription).filter(Transcription.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Save transcription text to storage
    try:
        storage_service = get_storage_service()
        storage_service.save_transcription_text(str(job.id), result.text)
        job.storage_path = f"{job.id}.txt.gz"
        logger.info(f"Saved transcription text for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to save transcription text for job {job_id}: {e}")
        # Don't fail the job if text save fails, log and continue

    # Save segments if provided (for individual timestamp preservation)
    if result.segments:
        try:
            storage_service = get_storage_service()
            storage_service.save_transcription_segments(str(job.id), result.segments)
            job.segments_path = f"{job.id}.segments.json.gz"
            logger.info(f"Saved {len(result.segments)} segments for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to save segments for job {job_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Save summary to database if provided
    if result.summary:
        try:
            from app.models.summary import Summary

            # Check if summary already exists
            existing_summary = db.query(Summary).filter(
                Summary.transcription_id == job.id
            ).first()

            if not existing_summary:
                new_summary = Summary(
                    transcription_id=job.id,
                    summary_text=result.summary,
                    model_name=os.getenv("GLM_MODEL", "GLM-4.5-Air")
                )
                db.add(new_summary)
                logger.info(f"Saved summary to database for job {job_id}")
            else:
                logger.info(f"Summary already exists for job {job_id}, skipping")
        except Exception as e:
            logger.error(f"Failed to save summary to database for job {job_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Save NotebookLM guideline if provided
    if result.notebooklm_guideline:
        try:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            storage_service.save_notebooklm_guideline(str(job.id), result.notebooklm_guideline)
            logger.info(f"Saved NotebookLM guideline for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to save NotebookLM guideline for job {job_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Update job status
    job.status = TranscriptionStatus.COMPLETED
    job.stage = "completed"
    job.completed_at = datetime.now(timezone.utc)
    job.processing_time_seconds = result.processing_time_seconds

    # Save audio duration if provided
    if result.duration_seconds is not None:
        job.duration_seconds = result.duration_seconds

    # Save language if provided (may be detected by Whisper)
    if result.language:
        job.language = result.language

    # Delete audio file to save disk space
    audio_deleted = False
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
            job.file_path = None
            audio_deleted = True
            logger.info(f"Deleted audio file for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to delete audio file for job {job_id}: {e}")

    db.commit()
    logger.info(f"Job {job_id} completed in {result.processing_time_seconds}s")

    return {
        "status": "completed",
        "job_id": str(job.id),
        "audio_deleted": audio_deleted
    }


@router.post("/jobs/{job_id}/fail")
async def fail_job(
    job_id: str,
    error_message: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Report job failure.

    Args:
        job_id: UUID of the transcription job
        error_message: Error message describing the failure
        db: Database session
        api_key: Verified runner API key

    Returns:
        Failure status
    """
    from datetime import datetime, timezone
    from app.db.base_class import Base
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(Transcription).filter(Transcription.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = TranscriptionStatus.FAILED
    job.stage = "failed"
    job.error_message = error_message
    job.completed_at = datetime.now(timezone.utc)

    db.commit()
    logger.error(f"Job {job_id} failed: {error_message}")

    return {
        "status": "failed",
        "job_id": str(job.id),
        "error": error_message
    }


@router.get("/audio/{job_id}", response_model=AudioDownloadResponse)
async def get_audio(
    job_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Get audio file information for processing.

    Returns the audio file path, metadata, and download URL for the runner.
    - For local/shared volume: Use file_path directly
    - For remote runners: Use download_url to fetch via HTTP

    Args:
        job_id: UUID of the transcription job
        db: Database session
        api_key: Verified runner API key

    Returns:
        Audio file information including download URL
    """
    from app.db.base_class import Base
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(Transcription).filter(Transcription.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check file_path first, then storage_path for backwards compatibility
    file_path = job.file_path
    if not file_path and job.storage_path:
        file_path = job.storage_path

    if not file_path:
        raise HTTPException(status_code=404, detail="Audio file path not set")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found at path: {file_path}"
        )

    file_size = os.path.getsize(file_path)

    # Always return download URL (use PUBLIC_BASE_URL or SERVER_URL from request context)
    # For simplicity, always use /api/runner/audio/{job_id}/download - runner will use the server URL
    download_url = f"/api/runner/audio/{job_id}/download"

    logger.info(f"Audio file info for job {job_id}: path={file_path}, size={file_size}")

    return AudioDownloadResponse(
        file_path=file_path,
        file_size=file_size,
        content_type="audio/mpeg",
        download_url=download_url
    )


@router.get("/audio/{job_id}/download")
async def download_audio(
    job_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Download the actual audio file for a job.

    This endpoint is used by remote runners to fetch audio files via HTTP.
    The file is streamed directly to the runner.

    Args:
        job_id: UUID of the transcription job
        db: Database session
        api_key: Verified runner API key

    Returns:
        Audio file as FileResponse
    """
    import uuid

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(Transcription).filter(Transcription.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check file_path first, then storage_path for backwards compatibility
    file_path = job.file_path
    if not file_path and job.storage_path:
        file_path = job.storage_path

    if not file_path:
        raise HTTPException(status_code=404, detail="Audio file path not set")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found at path: {file_path}"
        )

    logger.info(f"Downloading audio for job {job_id}: {file_path}")

    # Stream the file to the runner
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=job.file_name,
        headers={
            "Content-Disposition": f"attachment; filename={job.file_name}"
        }
    )


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def runner_heartbeat(
    request: HeartbeatRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_runner)
):
    """
    Update runner heartbeat (optional, for monitoring).

    This endpoint can be used to track runner health and current job load.
    In production, this could update a runners table for monitoring.

    Args:
        request: Heartbeat data with runner_id and current_jobs count
        db: Database session
        api_key: Verified runner API key

    Returns:
        Heartbeat acknowledgement
    """
    logger.debug(f"Heartbeat from runner {request.runner_id}: {request.current_jobs} active jobs")

    # In production, you could update a runners table here:
    # runner = db.query(Runner).filter(Runner.id == request.runner_id).first()
    # if runner:
    #     runner.last_ping = datetime.utcnow()
    #     runner.current_jobs = request.current_jobs
    #     db.commit()

    return HeartbeatResponse(status="ok")
