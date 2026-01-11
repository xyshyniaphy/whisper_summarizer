from pydantic import BaseModel, UUID4, ConfigDict, Field, field_serializer
from typing import Optional, Literal
from datetime import datetime
from pathlib import Path

class ShareLinkBase(BaseModel):
    transcription_id: UUID4

class ShareLinkCreate(ShareLinkBase):
    pass

class ShareLinkInDBBase(BaseModel):
    id: UUID4
    transcription_id: UUID4
    share_token: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int

    model_config = ConfigDict(from_attributes=True)

class ShareLink(ShareLinkInDBBase):
    """Share link with public URL included."""
    share_url: Optional[str] = None

class SharedTranscriptionResponse(BaseModel):
    """Response for shared transcription access (no auth required)."""
    id: UUID4
    file_name: str
    text: str  # AI-formatted transcription text (with punctuation and paragraphs)
    summary: Optional[str] = None  # AI summary
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedChatRequest(BaseModel):
    """Request schema for anonymous chat via shared link."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User message content"
    )


class SharedChatResponse(BaseModel):
    """Response schema for anonymous chat via shared link."""
    role: Literal["assistant"]
    content: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(
            datetime.now().tzinfo
        ).isoformat()
    )
