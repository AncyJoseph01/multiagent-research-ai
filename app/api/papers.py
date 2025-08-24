from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.paper import Paper, PaperCreate

router = APIRouter()


# Create a new paper
@router.post("/", response_model=Paper)
async def create_paper(paper: PaperCreate):
    normalized_arxiv_id = paper.arxiv_id.lower() if paper.arxiv_id else None

    # Check duplicate arxiv_id if provided
    if normalized_arxiv_id:
        query = select(models.Paper).where(models.Paper.arxiv_id == normalized_arxiv_id)
        existing_paper = await database.fetch_one(query)
        if existing_paper:
            raise HTTPException(status_code=400, detail="Paper with this arxiv_id already exists")

    paper_id = uuid.uuid4()
    query = insert(models.Paper).values(
        id=paper_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        arxiv_id=normalized_arxiv_id,
        url=paper.url,
        published_at=paper.published_at,
        created_at=datetime.utcnow(),
        user_id=paper.user_id,
    )
    await database.execute(query)

    return Paper(
        id=paper_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        arxiv_id=normalized_arxiv_id,
        url=paper.url,
        published_at=paper.published_at,
        created_at=datetime.utcnow(),
        user_id=paper.user_id,
    )


# Get all papers
@router.get("/", response_model=List[Paper])
async def read_papers():
    query = select(models.Paper)
    rows = await database.fetch_all(query)
    
    # Create a list of Paper Pydantic models from the fetched rows
    papers = [Paper.model_validate(row) for row in rows]
    
    return papers


# Get a paper by ID
@router.get("/{paper_id}", response_model=Paper)
async def read_paper(paper_id: uuid.UUID):
    query = select(models.Paper).where(models.Paper.id == paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


# Update a paper
@router.put("/{paper_id}", response_model=Paper)
async def update_paper(paper_id: uuid.UUID, updated_paper: PaperCreate):
    query = select(models.Paper).where(models.Paper.id == paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    normalized_arxiv_id = updated_paper.arxiv_id.lower() if updated_paper.arxiv_id else None

    # Ensure arxiv_id is unique
    if normalized_arxiv_id:
        dup_check = (
            select(models.Paper)
            .where(models.Paper.arxiv_id == normalized_arxiv_id, models.Paper.id != paper_id)
        )
        existing_paper = await database.fetch_one(dup_check)
        if existing_paper:
            raise HTTPException(status_code=400, detail="Another paper with this arxiv_id already exists")

    q = (
        update(models.Paper)
        .where(models.Paper.id == paper_id)
        .values(
            title=updated_paper.title,
            abstract=updated_paper.abstract,
            authors=updated_paper.authors,
            arxiv_id=normalized_arxiv_id,
            url=updated_paper.url,
            published_at=updated_paper.published_at,
            user_id=updated_paper.user_id,
        )
    )
    await database.execute(q)

    return Paper(
        id=paper_id,
        title=updated_paper.title,
        abstract=updated_paper.abstract,
        authors=updated_paper.authors,
        arxiv_id=normalized_arxiv_id,
        url=updated_paper.url,
        published_at=updated_paper.published_at,
        created_at=paper["created_at"],
        user_id=updated_paper.user_id,
    )


# Delete a paper
@router.delete("/{paper_id}")
async def delete_paper(paper_id: uuid.UUID):
    query = select(models.Paper).where(models.Paper.id == paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    q = delete(models.Paper).where(models.Paper.id == paper_id)
    await database.execute(q)

    return {"message": "Paper deleted successfully"}
