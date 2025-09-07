from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from uuid import UUID
from datetime import date, datetime
import logging
import uuid
from sqlalchemy import select, update, insert

from app.db.database import database
from app.db.models import Paper, Summary
from app.services.research_assistant import pdf_service, summariser_service, embedding_service
from app.schema.paper import Paper as PaperSchema

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_and_save_pdf(paper_id: uuid.UUID, content: str):
    """Summarise PDF content, save summary and embeddings, mark paper as done."""
    try:
        # Check if paper exists
        paper_row = await database.fetch_one(select(Paper).where(Paper.id == paper_id))
        if not paper_row:
            logger.warning(f"Paper {paper_id} not found. Skipping summary and embeddings.")
            return

        now = datetime.utcnow()

        # 1️⃣ Summarise
        summary_text = summariser_service.summarise_text(content)
        summary_data = {
            "id": uuid.uuid4(),
            "paper_id": paper_id,
            "summary_type": "structured",
            "content": summary_text,
            "created_at": now,
        }
        await database.execute(insert(Summary).values(summary_data))
        logger.info(f"Saved summary for paper {paper_id}")

        # 2️⃣ Chunk & embed
        chunks = pdf_service.split_text_into_chunks(content)
        await embedding_service.create_and_save_embeddings(paper_id, chunks)
        logger.info(f"Saved embeddings for paper {paper_id}")

        # 3️⃣ Update status
        await database.execute(
            update(Paper)
            .where(Paper.id == paper_id)
            .values(status="done")
        )
        logger.info(f"Paper {paper_id} marked as done")

    except Exception as e:
        logger.error(f"Processing failed for paper {paper_id}", exc_info=True)
        await database.execute(
            update(Paper)
            .where(Paper.id == paper_id)
            .values(status="failed")
        )


@router.post("/papers/upload", response_model=PaperSchema)
async def upload_and_summarise_pdf_paper(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: str = Form(...),
    abstract: str = Form(None),
    user_id: str = Form(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a PDF, extract text, save/update paper metadata,
    then summarise and embed content (background or immediate).
    """
    try:
        # Validate user UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a UUID.")

        # Validate PDF
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        extracted_text = pdf_service.extract_pdf_text(pdf_content)
        if not extracted_text or extracted_text.isspace():
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")

        # Normalize authors
        authors_str = ", ".join([a.strip() for a in authors.split(",")]) if authors else ""

        now = datetime.utcnow()

        # 1️⃣ Check for existing paper by user + title
        existing_paper = await database.fetch_one(
            select(Paper).where(Paper.user_id == user_uuid, Paper.title == title)
        )

        if existing_paper:
            # Update existing paper
            paper_id = existing_paper["id"]
            await database.execute(
                update(Paper)
                .where(Paper.id == paper_id)
                .values(
                    abstract=abstract or "No abstract provided.",
                    authors=authors_str,
                    published_at=date.today(),
                    status="processing",
                    created_at=now,
                )
            )
            logger.info(f"Updated existing paper record: {title}")
        else:
            # Insert new paper
            paper_id = uuid.uuid4()
            paper_data = {
                "id": paper_id,
                "title": title,
                "abstract": abstract or "No abstract provided.",
                "authors": authors_str,
                "arxiv_id": None,
                "url": None,
                "published_at": date.today(),
                "created_at": now,
                "user_id": user_uuid,
                "status": "processing",
            }
            await database.execute(insert(Paper).values(**paper_data))
            logger.info(f"Inserted new paper record: {title}")

        # 2️⃣ Process summary & embeddings
        if background_tasks:
            background_tasks.add_task(process_and_save_pdf, paper_id, extracted_text)
        else:
            await process_and_save_pdf(paper_id, extracted_text)

        # 3️⃣ Return the current paper record
        paper_row = await database.fetch_one(select(Paper).where(Paper.id == paper_id))
        return PaperSchema(**paper_row)

    except HTTPException as e:
        logger.error(f"HTTPException processing uploaded PDF: {title}", exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"Failed to process uploaded PDF: {title}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
