import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from sqlalchemy import insert
from datetime import date
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import database
from app.db.models import Paper, Summary, Embedding
from app.services.research_assistant import (
    arxiv_service,
    embedding_service,
    pdf_service,
    summariser_service,
)
from app.schema.paper import Paper as PaperSchema
from app.schema.summary import SummaryCreate
from app.schema.embedding import EmbeddingCreate
from datetime import datetime

from app.services.research_assistant.process_and_save_paper import process_and_save_paper 

logger = logging.getLogger(__name__)

router = APIRouter()

# For a simple MVP, let's use a placeholder user ID.
MOCK_USER_ID = uuid.UUID("bc3283ba-3093-423d-94a4-6482fddd27ff")

# This endpoint handles user PDF uploads
@router.post("/papers/upload", response_model=PaperSchema)
async def upload_and_summarise_pdf_paper(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: str = Form(...),
    abstract: Optional[str] = Form(None),
):
    """
    Uploads a PDF, extracts its content, and processes it for summarization and embedding.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are supported.")

    logger.info(f"Received PDF upload for '{title}' by {authors}")

    try:
        # Step 1: Read the content of the uploaded PDF file
        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Step 2: Extract text from the PDF content
        extracted_text = pdf_service.extract_pdf_text(pdf_content)
        if not extracted_text or extracted_text.isspace():
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")

        # Step 3: Process and save the paper using the extracted text and provided metadata
        processed_paper = await process_and_save_paper(
            title=title,
            abstract=abstract or "No abstract provided.",
            authors=authors,
            arxiv_id=None,  # No Arxiv ID for a user-uploaded file
            url=None,       # No URL for a user-uploaded file
            published_at=date.today(),  # Use the current date
            content=extracted_text,
            user_id=MOCK_USER_ID,
        )

        logger.info(f"Successfully processed and saved uploaded paper: {title}")
        return processed_paper

    except HTTPException as e:
        logger.error(f"HTTPException processing uploaded PDF: {title}", exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"Failed to process uploaded PDF: {title}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
