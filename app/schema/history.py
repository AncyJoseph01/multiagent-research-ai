from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class HistoryBase(BaseModel):
    query: str
    response: Optional[str] = None

class HistoryCreate(HistoryBase):
    user_id: uuid.UUID

class History(HistoryBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True