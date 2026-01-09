"""
Admin API Schemas

Pydantic schemas for user management, channel management, and admin operations.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ========================================
# User Management Schemas
# ========================================

class UserResponse(BaseModel):
    """User response with activation and admin status."""
    id: UUID
    email: EmailStr
    is_active: bool
    is_admin: bool
    activated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserActivateRequest(BaseModel):
    """Request to activate a user account."""
    is_active: bool = True


class UserAdminToggleRequest(BaseModel):
    """Request to toggle user admin status."""
    is_admin: bool


# ========================================
# Channel Management Schemas
# ========================================

class ChannelBase(BaseModel):
    """Base channel schema."""
    name: str
    description: Optional[str] = None


class ChannelCreate(ChannelBase):
    """Schema for creating a new channel."""
    pass


class ChannelUpdate(BaseModel):
    """Schema for updating a channel."""
    name: Optional[str] = None
    description: Optional[str] = None


class ChannelResponse(ChannelBase):
    """Channel response with metadata."""
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ChannelMemberResponse(BaseModel):
    """Channel membership response."""
    channel_id: UUID
    user_id: UUID
    assigned_at: datetime
    assigned_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ChannelDetailResponse(ChannelResponse):
    """Channel detail with members list."""
    members: List[UserResponse] = []


class UserWithChannelsResponse(UserResponse):
    """User response with channel memberships."""
    channels: List[ChannelResponse] = []


# ========================================
# Channel Assignment Schemas
# ========================================

class ChannelAssignmentRequest(BaseModel):
    """Request to assign users to a channel."""
    user_id: UUID


class TranscriptionChannelAssignmentRequest(BaseModel):
    """Request to assign transcription to channels."""
    channel_ids: List[UUID]


class TranscriptionChannelsResponse(BaseModel):
    """Response showing transcription's channel assignments."""
    transcription_id: UUID
    channels: List[ChannelResponse]


# ========================================
# Admin Audio Management Schemas
# ========================================

class AdminTranscriptionResponse(BaseModel):
    """Transcription response for admin (includes all)."""
    id: UUID
    user_id: Optional[UUID] = None
    file_name: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    stage: str
    error_message: Optional[str] = None
    pptx_status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    channels: List[ChannelResponse] = []

    class Config:
        from_attributes = True


class AdminTranscriptionListResponse(BaseModel):
    """Admin transcription list response."""
    total: int
    items: List[AdminTranscriptionResponse]
