import uuid
import logging
from fastapi import HTTPException
from sqlalchemy import update, select
from sqlalchemy.dialects.postgresql import insert
from datetime import date, datetime
from typing import Optional

from app.db.database import database
from app.db.models import Paper, Summary
from app.services.research_assistant import embedding_service, pdf_service, summariser_service
from app.schema.paper import Paper as PaperSchema

logger = logging.getLogger(__name__)

async def process_and_save_paper(
    title: str,
    abstract: str,
    authors: str,
    arxiv_id: Optional[str],
    url: Optional[str],
    published_at: Optional[date],
    content: str,
    user_id: uuid.UUID
) -> PaperSchema:
    """Helper function to process and save a paper, its summary, and embeddings."""
    now = datetime.utcnow()
    try:
        logger.info(f"Starting to process paper: {title}")

        # Step 1: Insert paper metadata (conflict-safe on user_id + arxiv_id)
        paper_data = {
            "id": uuid.uuid4(),
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "arxiv_id": arxiv_id,
            "url": url,
            "published_at": published_at,
            "created_at": now,
            "user_id": user_id,
            "status": "processing",
        }

        insert_query = insert(Paper).values(**paper_data).on_conflict_do_nothing(
            index_elements=[Paper.user_id, Paper.arxiv_id]
        )
        await database.execute(insert_query)

        # Step 2: Fetch the actual paper record (whether inserted or existing)
        paper_row = await database.fetch_one(
            select(Paper).where(Paper.user_id == user_id, Paper.arxiv_id == arxiv_id)
        )
        if not paper_row:
            raise HTTPException(status_code=500, detail="Failed to fetch or insert paper")
        
        paper_id = paper_row["id"]

        # Step 3: Summarise and save content
        summary_text = summariser_service.summarise_text(content)
        summary_data = {
            "id": uuid.uuid4(),
            "paper_id": paper_id,
            "summary_type": "structured",
            "content": summary_text,
            "created_at": now,
        }
        await database.execute(insert(Summary).values(summary_data))
        logger.info(f"Saved structured summary for paper {paper_id}")

        # Step 4: Chunk content and save embeddings
        chunks = pdf_service.split_text_into_chunks(content)
        await embedding_service.create_and_save_embeddings(paper_id, chunks)
        logger.info(f"Saved embeddings for paper {paper_id}")

        # Step 5: Update paper status to done
        await database.execute(
            update(Paper)
            .where(Paper.id == paper_id)
            .values(status="done")
        )
        logger.info(f"Paper {paper_id} marked as done")

        return PaperSchema(**paper_row)

    except Exception as e:
        logger.error(f"Failed to process paper: {title}", exc_info=True)

        # Optional: mark as failed if paper exists
        if 'paper_id' in locals():
            await database.execute(
                update(Paper)
                .where(Paper.id == paper_id)
                .values(status="failed")
            )

        raise HTTPException(status_code=500, detail=f"Failed to process paper: {str(e)}")
