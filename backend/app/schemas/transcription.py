from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional, List
from datetime import datetime
# Circular import avoidance might be needed if Summary schema includes Transcription
# from .summary import Summary

class TranscriptionBase(BaseModel):
    file_name: str
    status: Optional[str] = "processing"
    language: Optional[str] = None
    duration_seconds: Optional[float] = None

class TranscriptionCreate(TranscriptionBase):
    pass

class TranscriptionUpdate(TranscriptionBase):
    original_text: Optional[str] = None
    status: Optional[str] = None

class TranscriptionInDBBase(TranscriptionBase):
    id: UUID4
    user_id: Optional[UUID4] = None
    original_text: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Transcription(TranscriptionInDBBase):
    pass
    # summaries: List["Summary"] = [] # Type checking issues might arise
