import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import insert
from datetime import date
from typing import List

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

logger = logging.getLogger(__name__)

router = APIRouter()

# For a simple MVP, let's use a placeholder user ID. In a real app, this would come from authentication.
MOCK_USER_ID = uuid.UUID("bc3283ba-3093-423d-94a4-6482fddd27ff")

async def process_and_save_paper(
    title: str,
    abstract: str,
    authors: str,
    arxiv_id: str,
    url: str,
    published_at: date,
    content: str,
    user_id: uuid.UUID
) -> PaperSchema:
    """Helper function to process and save a paper, its summary, and embeddings."""
    paper_id = uuid.uuid4()
    now = datetime.utcnow()
    try:
        logger.info(f"Starting to process paper: {title}")

        # Save paper metadata
        paper_data = {
            "id": paper_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "arxiv_id": arxiv_id,
            "url": url,
            "published_at": published_at,
            "created_at": now,
            "user_id": user_id,
        }
        await database.execute(insert(Paper).values(**paper_data))
        logger.info(f"Saved paper metadata with ID: {paper_id}")

        # Summarise and save content
        logger.info("Calling summarisation service...")
        summary_content = summariser_service.summarise_text(content)
        
        summary_data = {
            "id": uuid.uuid4(),  
            "paper_id": paper_id,
            "summary_type": "structured",
            "content": summary_content,
            "created_at": now, 
        }
        await database.execute(insert(Summary).values(summary_data))
        logger.info("Saved structured summary.")

        # --- CORRECT CODE FOR CHUNKING AND EMBEDDING ---
        logger.info("Splitting content into chunks for embedding.")
        chunks = pdf_service.split_text_into_chunks(content)

        logger.info(f"Creating and saving embeddings for {len(chunks)} chunks.")
        await embedding_service.create_and_save_embeddings(paper_id, chunks)

        logger.info("Finished processing.")
        
        return PaperSchema(**paper_data)
    except Exception as e:
        logger.error(f"Failed to process paper: {title}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process paper: {str(e)}")

# This endpoint handles all ArXiv requests
@router.post("/papers/arxiv", response_model=List[PaperSchema])
async def fetch_and_summarise_arxiv_papers(keyword: str, max_results: int = 5):
    """Fetches papers from Arxiv, summarises them, and stores the results."""
    logger.info(f"Received request to fetch papers for keyword: '{keyword}' with max_results={max_results}")
    
    papers_metadata = arxiv_service.fetch_arxiv_papers(keyword, max_results)
    logger.info(f"Found {len(papers_metadata)} papers from Arxiv.")

    saved_papers = []
    for paper in papers_metadata:
        try:
            logger.info(f"Processing paper: {paper['title']}")
            
            # Step 1: Download the full PDF content
            # The 'arxiv_service' must have a 'download_pdf_content' function
            pdf_content = await arxiv_service.download_pdf_content(paper["pdf_url"])
            if not pdf_content:
                logger.warning(f"Skipping paper due to PDF download failure: {paper['title']}")
                continue

            # Step 2: Extract text from the downloaded PDF
            extracted_text = pdf_service.extract_pdf_text(pdf_content)
            if not extracted_text or extracted_text.isspace():
                logger.warning(f"Skipping paper due to empty or unreadable text: {paper['title']}")
                continue

            # Step 3: Process and save the paper using the full text
            processed_paper = await process_and_save_paper(
                title=paper["title"],
                abstract=paper["abstract"],
                authors=paper["authors"],
                arxiv_id=paper["arxiv_id"],
                url=paper["url"],
                published_at=paper["published_at"],
                content=extracted_text,
                user_id=MOCK_USER_ID,
            )
            saved_papers.append(processed_paper)
            logger.info(f"Successfully processed and saved paper: {paper['title']}")

        except HTTPException as e:
            logger.error(f"HTTPException processing Arxiv paper: {paper.get('title', 'Unknown')}", exc_info=True)
            # Re-raise HTTPException to show the user a proper error
            raise e
        except Exception as e:
            logger.error(f"Failed to process Arxiv paper: {paper.get('title', 'Unknown')}", exc_info=True)
            # You can decide to re-raise or just log and continue
            continue # This will skip the current paper and move to the next
    
    logger.info("Finished processing all Arxiv papers.")
    return saved_papers