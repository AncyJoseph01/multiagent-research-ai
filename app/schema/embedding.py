from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class EmbeddingBase(BaseModel):
    chunk_id: Optional[int] = None
    vector: List[float]

class EmbeddingCreate(EmbeddingBase):
    paper_id: uuid.UUID

class Embedding(EmbeddingBase):
    id: uuid.UUID
    created_at: datetime
    paper_id: uuid.UUID

    class Config:
        from_attributes = True