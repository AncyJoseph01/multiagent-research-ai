from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import uuid

class PaperBase(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[date] = None

class PaperCreate(PaperBase):
    user_id: uuid.UUID

class Paper(PaperBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True