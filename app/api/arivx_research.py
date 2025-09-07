import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime

from app.db.database import database
from app.db.models import Paper, Summary
from app.services.research_assistant import (
    arxiv_service,
    embedding_service,
    pdf_service,
    summariser_service,
)
from app.schema.paper import Paper as PaperSchema

logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------------------
# Background processing function
# ------------------------------
async def process_and_save_paper(paper_id: uuid.UUID, content: str):
    """
    Summarises text, saves summary & embeddings, and updates status.
    """
    try:
        # Check if paper exists
        paper_exists = await database.fetch_one(select(Paper).where(Paper.id == paper_id))
        if not paper_exists:
            logger.warning(f"Paper {paper_id} not found. Skipping summary and embeddings.")
            return

        now = datetime.utcnow()

        # Summarise
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

        # Split into chunks and embed
        chunks = pdf_service.split_text_into_chunks(content)
        await embedding_service.create_and_save_embeddings(paper_id, chunks)
        logger.info(f"Saved embeddings for paper {paper_id}")

        # Update status to done
        await database.execute(
            update(Paper)
            .where(Paper.id == paper_id)
            .values(status="done")
        )
        logger.info(f"Paper {paper_id} marked as done")

    except Exception as e:
        logger.error(f"Processing failed for paper {paper_id}", exc_info=True)
        # Update status to failed
        await database.execute(
            update(Paper)
            .where(Paper.id == paper_id)
            .values(status="failed")
        )

# ------------------------------
# Endpoint: Fetch Arxiv Papers
# ------------------------------
@router.post("/papers/arxiv", response_model=list[PaperSchema])
async def fetch_and_summarise_arxiv_papers(
    keyword: str,
    background_tasks: BackgroundTasks,
    user_id: str = Query(...),
    max_results: int = 1,
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    papers_metadata = arxiv_service.fetch_arxiv_papers(keyword, max_results)
    now = datetime.utcnow()
    saved_papers = []

    for paper in papers_metadata:
        paper_id = uuid.uuid4()
        paper_data = {
            "id": paper_id,
            "title": paper["title"],
            "abstract": paper["abstract"],
            "authors": paper["authors"],
            "arxiv_id": paper["arxiv_id"],
            "url": paper["url"],
            "published_at": paper["published_at"],
            "created_at": now,
            "user_id": user_uuid,
            "status": "processing",
        }

        # Insert placeholder, avoiding duplicates using user_id + arxiv_id
        await database.execute(
            insert(Paper)
            .values(**paper_data)
            .on_conflict_do_update(
                index_elements=[Paper.user_id, Paper.arxiv_id],
                set_={
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "authors": paper["authors"],
                    "url": paper["url"],
                    "published_at": paper["published_at"],
                    "status": "processing",
                },
            )
        )

        saved_papers.append(PaperSchema(**paper_data))

        # Start background processing only if PDF exists
        try:
            pdf_url = paper.get("pdf_url")
            if pdf_url:
                pdf_content = await arxiv_service.download_pdf_content(pdf_url)
                if pdf_content:
                    extracted_text = pdf_service.extract_pdf_text(pdf_content)
                    if extracted_text and not extracted_text.isspace():
                        background_tasks.add_task(process_and_save_paper, paper_id, extracted_text)
        except Exception as e:
            logger.warning(f"Background task skipped for paper {paper_id}: {e}")
            # Immediately mark as failed if PDF can't be processed
            await database.execute(
                update(Paper)
                .where(Paper.id == paper_id)
                .values(status="failed")
            )

    return saved_papers
