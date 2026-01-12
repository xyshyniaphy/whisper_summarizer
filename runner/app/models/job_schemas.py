"""Job schemas for runner-server communication"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class Job(BaseModel):
    """Job details from server."""
    id: str
    file_name: str
    file_path: Optional[str] = None
    storage_path: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime


class JobResult(BaseModel):
    """Result of processing a job."""
    text: str
    segments: Optional[List[Dict]] = None  # Whisper segments with individual timestamps
    summary: Optional[str] = None
    notebooklm_guideline: Optional[str] = None
    processing_time_seconds: int


class JobStartResponse(BaseModel):
    """Response when starting a job."""
    status: str
    job_id: str


class JobCompleteResponse(BaseModel):
    """Response when completing a job."""
    status: str
    job_id: str
    audio_deleted: bool


class JobFailResponse(BaseModel):
    """Response when failing a job."""
    status: str
    job_id: str
    error: str


class AudioInfo(BaseModel):
    """Audio file information."""
    file_path: str
    file_size: int
    content_type: Optional[str] = None
