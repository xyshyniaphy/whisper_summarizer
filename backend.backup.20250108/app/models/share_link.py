from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base_class import Base

class ShareLink(Base):
    """Public share links for transcriptions."""
    __tablename__ = "share_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Unique token for public access (URL-safe base64)
    share_token = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    access_count = Column(Integer, default=0, nullable=False)  # Track access count

    transcription = relationship("Transcription", back_populates="share_links", passive_deletes=True)
