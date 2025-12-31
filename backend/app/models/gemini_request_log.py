"""
Gemini API Request Log Model
Stores detailed information about Gemini API requests for debugging
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base_class import Base


class GeminiRequestLog(Base):
    """Detailed log of Gemini API requests for debugging and analysis"""
    __tablename__ = "gemini_request_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request information
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id"), nullable=False)
    file_name = Column(String(500), nullable=True)  # Original filename
    model_name = Column(String(100), nullable=False)  # e.g., gemini-2.0-flash-exp

    # Input/Output
    prompt = Column(Text, nullable=False)  # System prompt used
    input_text = Column(Text, nullable=False)  # Transcription text (may be truncated)
    input_text_length = Column(Integer, nullable=False)  # Character count of input
    output_text = Column(Text, nullable=True)  # Generated summary
    output_text_length = Column(Integer, nullable=True)  # Character count of output

    # Token usage (if available from API response)
    input_tokens = Column(Integer, nullable=True)  # Input token count
    output_tokens = Column(Integer, nullable=True)  # Output token count
    total_tokens = Column(Integer, nullable=True)  # Total token count

    # Performance metrics
    response_time_ms = Column(Float, nullable=True)  # API response time in milliseconds
    temperature = Column(Float, nullable=True)  # Temperature setting used

    # Status
    status = Column(String(50), nullable=False, default="success")  # success, error, timeout
    error_message = Column(Text, nullable=True)  # Error details if failed

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    transcription = relationship("Transcription", backref="gemini_logs")
