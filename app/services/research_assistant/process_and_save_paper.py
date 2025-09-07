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
