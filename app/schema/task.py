from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class TaskBase(BaseModel):
    description: str
    due_date: Optional[datetime] = None
    status: Optional[str] = "pending"

class TaskCreate(TaskBase):
    user_id: uuid.UUID

class Task(TaskBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True