from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base_class import Base

class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(Text, nullable=True)
    # Path to compressed text file in Supabase Storage (format: {uuid}.txt.gz)
    storage_path = Column(String, nullable=True)
    status = Column(String, default="processing")  # Legacy, use stage instead
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

    @property
    def text(self) -> str:
        """
        Get the decompressed transcription text from Supabase Storage.

        The text is stored as a gzip-compressed file in Supabase Storage.
        This property downloads and decompresses it on demand.
        """
        if not self.storage_path:
            return ""

        try:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            return storage_service.get_transcription_text(str(self.id))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load transcription text from storage: {e}")
            return ""
