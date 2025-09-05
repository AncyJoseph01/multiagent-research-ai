from pydantic import BaseModel
from typing import Optional

class PaperUploadJSON(BaseModel):
    title: str
    authors: str
    abstract: Optional[str] = None
    user_id: str
    pdf_base64: str 
