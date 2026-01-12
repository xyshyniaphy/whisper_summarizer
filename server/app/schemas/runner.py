"""Runner API schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class JobResponse(BaseModel):
    """Job details returned to runner."""
    id: str
    file_name: str
    file_path: Optional[str] = None
    storage_path: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """List of jobs response."""
    jobs: List[JobResponse]
    count: int


class JobStartRequest(BaseModel):
    """Request to start/claim a job."""
    runner_id: str


class JobCompleteRequest(BaseModel):
    """Request to mark job as completed."""
    text: str
    segments: Optional[List[dict]] = None  # Whisper segments with timestamps
    summary: Optional[str] = None
    notebooklm_guideline: Optional[str] = None
    processing_time_seconds: int


class JobCompleteResponse(BaseModel):
    """Response after job completion."""
    status: str
    message: Optional[str] = None


class AudioDownloadResponse(BaseModel):
    """Audio file details for download."""
    file_path: str
    file_size: int
    content_type: Optional[str] = None
    download_url: Optional[str] = None  # HTTP download URL for remote runners


class HeartbeatRequest(BaseModel):
    """Runner heartbeat update."""
    runner_id: str
    current_jobs: int = 0


class HeartbeatResponse(BaseModel):
    """Heartbeat acknowledgement."""
    status: str
