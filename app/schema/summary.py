from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class SummaryBase(BaseModel):
    summary_type: Optional[str] = None
    content: str

class SummaryCreate(SummaryBase):
    paper_id: uuid.UUID

class Summary(SummaryBase):
    id: uuid.UUID
    created_at: datetime
    paper_id: uuid.UUID

    class Config:
        from_attributes = True