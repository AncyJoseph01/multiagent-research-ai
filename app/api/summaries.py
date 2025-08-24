from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.summary import Summary, SummaryCreate

router = APIRouter()


# Create a new summary
@router.post("/", response_model=Summary)
async def create_summary(summary: SummaryCreate):
    # Check if the paper exists
    query = select(models.Paper).where(models.Paper.id == summary.paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    summary_id = uuid.uuid4()
    query = insert(models.Summary).values(
        id=summary_id,
        summary_type=summary.summary_type,
        content=summary.content,
        created_at=datetime.utcnow(),
        paper_id=summary.paper_id,
    )
    await database.execute(query)

    return Summary(
        id=summary_id,
        summary_type=summary.summary_type,
        content=summary.content,
        created_at=datetime.utcnow(),
        paper_id=summary.paper_id,
    )


# Get all summaries
@router.get("/", response_model=List[Summary])
async def read_summaries():
    query = select(models.Summary)
    rows = await database.fetch_all(query)
    return rows


# Get a summary by ID
@router.get("/{summary_id}", response_model=Summary)
async def read_summary(summary_id: uuid.UUID):
    query = select(models.Summary).where(models.Summary.id == summary_id)
    summary = await database.fetch_one(query)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary


# Update a summary
@router.put("/{summary_id}", response_model=Summary)
async def update_summary(summary_id: uuid.UUID, updated_summary: SummaryCreate):
    # Check if the summary exists
    query = select(models.Summary).where(models.Summary.id == summary_id)
    summary = await database.fetch_one(query)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # Check if the paper exists
    query = select(models.Paper).where(models.Paper.id == updated_summary.paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    q = (
        update(models.Summary)
        .where(models.Summary.id == summary_id)
        .values(
            summary_type=updated_summary.summary_type,
            content=updated_summary.content,
            paper_id=updated_summary.paper_id,
        )
    )
    await database.execute(q)

    return Summary(
        id=summary_id,
        summary_type=updated_summary.summary_type,
        content=updated_summary.content,
        created_at=summary["created_at"],
        paper_id=updated_summary.paper_id,
    )


# Delete a summary
@router.delete("/{summary_id}")
async def delete_summary(summary_id: uuid.UUID):
    query = select(models.Summary).where(models.Summary.id == summary_id)
    summary = await database.fetch_one(query)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    q = delete(models.Summary).where(models.Summary.id == summary_id)
    await database.execute(q)

    return {"message": "Summary deleted successfully"}
