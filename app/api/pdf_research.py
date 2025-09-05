from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from uuid import UUID
from datetime import date
import logging
from typing import Optional

from app.services.research_assistant import pdf_service
from app.services.research_assistant.process_and_save_paper import process_and_save_paper
from app.schema.paper import Paper as PaperSchema

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/papers/upload", response_model=PaperSchema)
async def upload_and_summarise_pdf_paper(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: str = Form(...),
    abstract: Optional[str] = Form(None),
    user_id: str = Form(...),  # <-- frontend sends user_id here
):
    """
    Uploads a PDF, extracts its content, and processes it for summarization and embedding.
    """
    try:
        # Validate user ID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a UUID.")

        # Validate PDF file
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are supported.")

        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        extracted_text = pdf_service.extract_pdf_text(pdf_content)
        if not extracted_text or extracted_text.isspace():
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")

        # Process and save the paper
        processed_paper = await process_and_save_paper(
            title=title,
            abstract=abstract or "No abstract provided.",
            authors=authors,
            arxiv_id=None,
            url=None,
            published_at=date.today(),
            content=extracted_text,
            user_id=user_uuid,
        )

        logger.info(f"Successfully processed and saved uploaded paper: {title}")

        # Normalize response
        response = PaperSchema.from_orm(processed_paper)
        return response

    except HTTPException as e:
        logger.error(f"HTTPException processing uploaded PDF: {title}", exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"Failed to process uploaded PDF: {title}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
