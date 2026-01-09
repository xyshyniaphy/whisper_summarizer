from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base_class import Base


class Channel(Base):
    """Channel model for organizing content into categories/topics."""
    __tablename__ = "channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    memberships = relationship("ChannelMembership", back_populates="channel", cascade="all, delete-orphan")
    transcription_assignments = relationship("TranscriptionChannel", back_populates="channel", cascade="all, delete-orphan")


class ChannelMembership(Base):
    """Junction table for users <-> channels many-to-many relationship."""
    __tablename__ = "channel_memberships"

    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="memberships")
    user = relationship("User", back_populates="channel_memberships", foreign_keys=[user_id])


class TranscriptionChannel(Base):
    """Junction table for transcriptions <-> channels many-to-many relationship."""
    __tablename__ = "transcription_channels"

    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), primary_key=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    transcription = relationship("Transcription", back_populates="channel_assignments")
    channel = relationship("Channel", back_populates="transcription_assignments")
