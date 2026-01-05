from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional
from datetime import datetime

class SummaryBase(BaseModel):
    summary_text: str
    model_name: Optional[str] = None

class SummaryCreate(SummaryBase):
    transcription_id: UUID4

class SummaryUpdate(SummaryBase):
    pass

class SummaryInDBBase(SummaryBase):
    id: UUID4
    transcription_id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Summary(SummaryInDBBase):
    pass
