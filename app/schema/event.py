from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    external_id: Optional[str] = None

class EventCreate(EventBase):
    user_id: uuid.UUID

class Event(EventBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True