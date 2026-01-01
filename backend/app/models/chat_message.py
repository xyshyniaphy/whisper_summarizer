from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base_class import Base

class ChatMessage(Base):
    """Chat messages for AI Q&A about transcriptions."""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transcription = relationship("Transcription", back_populates="chat_messages", passive_deletes=True)
