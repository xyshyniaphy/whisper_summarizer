from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone, timedelta
from app.db.base_class import Base

class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(Text, nullable=True)
    # Path to compressed text file in local filesystem (format: {uuid}.txt.gz)
    storage_path = Column(String, nullable=True)
    language = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Process tracking fields
    stage = Column(String, default="uploading", nullable=False)  # uploading, transcribing, summarizing, completed, failed
    error_message = Column(Text, nullable=True)  # Last error message
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retries attempted
    completed_at = Column(DateTime(timezone=True), nullable=True)  # When fully completed

    # PPTX generation status
    pptx_status = Column(String, default="not-started", nullable=False)  # not-started, generating, ready, error
    pptx_error_message = Column(Text, nullable=True)  # PPTX generation error details

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    # user = relationship("User", back_populates="transcriptions") # User model reference if needed
    summaries = relationship("Summary", back_populates="transcription", passive_deletes=True)
    gemini_logs = relationship("GeminiRequestLog", back_populates="transcription", passive_deletes=True)
    chat_messages = relationship("ChatMessage", back_populates="transcription", passive_deletes=True, order_by="ChatMessage.created_at")
    share_links = relationship("ShareLink", back_populates="transcription", passive_deletes=True)
    channel_assignments = relationship("TranscriptionChannel", back_populates="transcription", cascade="all, delete-orphan")

    @property
    def original_text(self) -> str:
        """
        Get the original unformatted transcription text from local filesystem.

        This reads from {uuid}.txt.gz which contains the raw Whisper output
        without AI formatting. Use this for operations that need original text
        (e.g., re-formatting, timestamp-based operations).
        """
        if not self.storage_path:
            return ""

        try:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            return storage_service.get_transcription_text(str(self.id))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load original transcription text from storage: {e}")
            return ""

    @property
    def text(self) -> str:
        """
        Get the transcription text, preferring AI-formatted version.

        Returns formatted text with punctuation and paragraphs added by the LLM.
        Falls back to original text if formatted version doesn't exist.

        This is the default property for displaying transcription content.
        """
        try:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            # Try formatted text first
            if storage_service.formatted_text_exists(str(self.id)):
                return storage_service.get_formatted_text(str(self.id))
            # Fall back to original text
            return storage_service.get_transcription_text(str(self.id))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load transcription text from storage: {e}")
            return ""

    @property
    def time_remaining(self) -> timedelta:
        """
        Calculate remaining time before auto-deletion.

        Returns a timedelta showing how long until this transcription
        will be automatically deleted based on MAX_KEEP_DAYS setting.
        Negative value means the item is past its retention period.
        """
        from app.core.config import settings
        max_age = timedelta(days=settings.MAX_KEEP_DAYS)
        age = datetime.now(timezone.utc) - self.created_at
        return max_age - age

    @property
    def is_expired(self) -> bool:
        """Check if this transcription has exceeded its retention period."""
        return self.time_remaining.total_seconds() <= 0
