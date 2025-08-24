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
MOCK_USER_ID = uuid.UUID("938b9f29-8e79-4dc1-a6b3-4ea1963bdc10")

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
    try:
        logger.info(f"Starting to process paper: {title}")

        # Save paper metadata
        paper_id = uuid.uuid4()
        paper_data = {
            "id": paper_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "arxiv_id": arxiv_id,
            "url": url,
            "published_at": published_at,
            "created_at": datetime.utcnow(),
            "user_id": user_id,
        }
        await database.execute(insert(Paper).values(**paper_data))
        logger.info(f"Saved paper metadata with ID: {paper_id}")

        logger.info("Calling summarisation service...")
        summary_content = summariser_service.summarise_text(content)
        
    
        summary_id = uuid.uuid4()
        
        summary_data = SummaryCreate(
            id=summary_id,  
            paper_id=paper_id,
            summary_type="structured",
            content=summary_content,
            created_at=datetime.utcnow(),
        )
        await database.execute(insert(Summary).values(summary_data.model_dump()))
        logger.info("Saved structured summary.")

        logger.info("Generating and saving embeddings...")
        embedding_vector = embedding_service.create_embedding(content)
        embedding_data = EmbeddingCreate(
            paper_id=paper_id,
            chunk_id=0,
            vector=embedding_vector,
        )
        await database.execute(insert(Embedding).values(embedding_data.model_dump()))
        logger.info("Embeddings saved successfully.")

        logger.info(f"Finished processing paper: {title}")
        return PaperSchema(**paper_data)
    except Exception as e:
        logger.error(f"Failed to process paper: {title}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process paper: {str(e)}")


@router.post("/papers/arxiv", response_model=List[PaperSchema])
async def fetch_and_summarise_arxiv_papers(keyword: str, max_results: int = 5):
    """Fetches papers from Arxiv, summarises them, and stores the results."""
    logger.info(f"Received request to fetch papers for keyword: '{keyword}' with max_results={max_results}")
    
    papers_metadata = arxiv_service.fetch_arxiv_papers(keyword, max_results)
    logger.info(f"Found {len(papers_metadata)} papers from Arxiv.")

    saved_papers = []
    for paper in papers_metadata:
        try:
            processed_paper = await process_and_save_paper(
                title=paper["title"],
                abstract=paper["abstract"],
                authors=paper["authors"],
                arxiv_id=paper["arxiv_id"],
                url=paper["url"],
                published_at=paper["published_at"],
                content=paper["abstract"],
                user_id=MOCK_USER_ID,
            )
            saved_papers.append(processed_paper)
        except HTTPException:
            pass

    logger.info("Finished processing all Arxiv papers.")
    return saved_papers


@router.post("/papers/upload", response_model=PaperSchema)
async def upload_and_summarise_pdf(
    file: UploadFile = File(...),
):
    """Extracts text from a PDF, summarises it, and stores the results."""
    logger.info(f"Received request to upload PDF file: {file.filename}")

    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type uploaded: {file.content_type}")
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDF files are supported."
        )

    try:
        logger.info("Reading and extracting text from PDF.")
        file_content = await file.read()
        extracted_text = pdf_service.extract_pdf_text(file_content)

        paper_title = file.filename or "Uploaded PDF"
        processed_paper = await process_and_save_paper(
            title=paper_title,
            abstract=extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            authors="N/A",
            arxiv_id=None,
            url=None,
            published_at=date.today(),
            content=extracted_text,
            user_id=MOCK_USER_ID,
        )
        logger.info("Finished processing PDF upload.")
        return processed_paper
    except Exception as e:
        logger.error("Failed to process PDF upload.", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")