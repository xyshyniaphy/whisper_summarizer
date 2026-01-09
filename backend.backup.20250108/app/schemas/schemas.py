"""
Pydanticスキーマ定義
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# ========================================
# 認証スキーマ (Google OAuthのみ)
# ========================================

class AuthResponse(BaseModel):
    """認証レスポンス (Google OAuth)"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict


# ========================================
# ユーザースキーマ
# ========================================

class UserBase(BaseModel):
    """ユーザーベーススキーマ"""
    email: EmailStr
    full_name: Optional[str] = None


class UserResponse(UserBase):
    """ユーザーレスポンス"""
    id: str
    email_confirmed_at: Optional[datetime] = None
    created_at: datetime


# ========================================
# 音声ファイルスキーマ
# ========================================

class AudioUploadResponse(BaseModel):
    """音声アップロードレスポンス"""
    id: UUID
    filename: str
    file_size: int
    status: str
    created_at: datetime


class AudioFileResponse(BaseModel):
    """音声ファイルレスポンス"""
    id: UUID
    filename: str
    file_size: int
    duration: Optional[int] = None
    status: str
    created_at: datetime
    transcription: Optional[dict] = None


# ========================================
# 文字起こしスキーマ
# ========================================

class TranscriptionResponse(BaseModel):
    """文字起こしレスポンス"""
    id: UUID
    audio_file_id: UUID
    content: str
    summary: Optional[str] = None
    language: str
    confidence: Optional[float] = None
    timestamps: Optional[list] = None
    created_at: datetime


class TranscriptionListResponse(BaseModel):
    """文字起こしリストレスポンス"""
    total: int
    items: list[TranscriptionResponse]
    limit: int
    offset: int
