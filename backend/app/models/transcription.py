from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, hybrid_property
import uuid
import gzip
from app.db.base_class import Base

class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(Text, nullable=True)
    original_text = Column(Text, nullable=True)  # Legacy, kept for backward compatibility
    original_text_compressed = Column(LargeBinary, nullable=True)  # Gzip-compressed binary data
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

    @hybrid_property
    def text(self) -> str:
        """
        Get the decompressed transcription text.
        Returns compressed data if available, otherwise falls back to original_text.
        """
        if self.original_text_compressed:
            try:
                return gzip.decompress(self.original_text_compressed).decode('utf-8')
            except Exception:
                # Fall back to original_text if decompression fails
                pass
        return self.original_text or ""
