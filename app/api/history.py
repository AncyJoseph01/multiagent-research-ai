from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.history import History, HistoryCreate

router = APIRouter()


# Create a new history record
@router.post("/", response_model=History)
async def create_history(history: HistoryCreate):
    # Check if the user exists
    query = select(models.User).where(models.User.id == history.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    history_id = uuid.uuid4()
    query = insert(models.History).values(
        id=history_id,
        query=history.query,
        response=history.response,
        created_at=datetime.utcnow(),
        user_id=history.user_id,
    )
    await database.execute(query)

    return History(
        id=history_id,
        query=history.query,
        response=history.response,
        created_at=datetime.utcnow(),
        user_id=history.user_id,
    )


# Get all history records
@router.get("/", response_model=List[History])
async def read_histories():
    query = select(models.History)
    rows = await database.fetch_all(query)
    return rows


# Get a history record by ID
@router.get("/{history_id}", response_model=History)
async def read_history(history_id: uuid.UUID):
    query = select(models.History).where(models.History.id == history_id)
    history = await database.fetch_one(query)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")
    return history


# Update a history record
@router.put("/{history_id}", response_model=History)
async def update_history(history_id: uuid.UUID, updated_history: HistoryCreate):
    # Check if the history record exists
    query = select(models.History).where(models.History.id == history_id)
    history = await database.fetch_one(query)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")

    # Check if the user exists
    query = select(models.User).where(models.User.id == updated_history.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        update(models.History)
        .where(models.History.id == history_id)
        .values(
            query=updated_history.query,
            response=updated_history.response,
            user_id=updated_history.user_id,
        )
    )
    await database.execute(q)

    return History(
        id=history_id,
        query=updated_history.query,
        response=updated_history.response,
        created_at=history["created_at"],
        user_id=updated_history.user_id,
    )


# Delete a history record
@router.delete("/{history_id}")
async def delete_history(history_id: uuid.UUID):
    query = select(models.History).where(models.History.id == history_id)
    history = await database.fetch_one(query)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")

    q = delete(models.History).where(models.History.id == history_id)
    await database.execute(q)

    return {"message": "History record deleted successfully"}
