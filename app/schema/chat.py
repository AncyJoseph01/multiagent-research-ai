from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class ChatRequest(BaseModel):
    query: str
    chat_session_id: Optional[int] = None 


class ChatResponse(BaseModel):
    id: uuid.UUID    
    chat_session_id: int
    user_id: uuid.UUID   
    query: str
    answer: str
    cot_transcript: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ChatHistory(BaseModel):
    chat_session_id: int
    chats: List[ChatResponse]


class ChatSessionInfo(BaseModel):
    chat_session_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chat_query: str = ""

    class Config:
        from_attributes = True
