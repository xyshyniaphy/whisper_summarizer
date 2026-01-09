from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional, List
from datetime import datetime

class ChatMessageBase(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatMessageCreate(ChatMessageBase):
    transcription_id: UUID4

class ChatMessageInDBBase(ChatMessageBase):
    id: UUID4
    transcription_id: UUID4
    user_id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatMessage(ChatMessageInDBBase):
    pass

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage] = []
