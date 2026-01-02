from pydantic import BaseModel, UUID4, ConfigDict, field_serializer
from typing import Optional, List
from datetime import datetime, timedelta

class SummaryBase(BaseModel):
    summary_text: str
    model_name: Optional[str] = None

class Summary(SummaryBase):
    id: UUID4
    transcription_id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TranscriptionBase(BaseModel):
    file_name: str
    status: Optional[str] = "processing"  # Legacy
    stage: Optional[str] = "uploading"
    language: Optional[str] = None
    duration_seconds: Optional[float] = None

class TranscriptionCreate(TranscriptionBase):
    pass

class TranscriptionUpdate(TranscriptionBase):
    status: Optional[str] = None
    stage: Optional[str] = None
    error_message: Optional[str] = None

class TranscriptionInDBBase(TranscriptionBase):
    id: UUID4
    user_id: Optional[UUID4] = None
    file_path: Optional[str] = None
    storage_path: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = 0
    completed_at: Optional[datetime] = None
    pptx_status: Optional[str] = "not-started"
    pptx_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Transcription(TranscriptionInDBBase):
    summaries: List[Summary] = []
    text: str = ""  # Transcription text (decompressed from storage)
    formatted_text: str = ""  # AI-formatted transcription text (with punctuation and paragraphs)
    time_remaining: Optional[timedelta] = None  # Time until auto-deletion (calculated)

    @field_serializer('time_remaining')
    def serialize_time_remaining(self, td: Optional[timedelta]) -> Optional[float]:
        """Serialize timedelta to total seconds remaining."""
        return td.total_seconds() if td else None
