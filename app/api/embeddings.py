from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.embedding import Embedding, EmbeddingCreate

router = APIRouter()


# Create a new embedding
@router.post("/", response_model=Embedding)
async def create_embedding(embedding: EmbeddingCreate):
    # Check if the paper exists
    query = select(models.Paper).where(models.Paper.id == embedding.paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    embedding_id = uuid.uuid4()
    query = insert(models.Embedding).values(
        id=embedding_id,
        chunk_id=embedding.chunk_id,
        vector=embedding.vector,
        created_at=datetime.utcnow(),
        paper_id=embedding.paper_id,
    )
    await database.execute(query)

    return Embedding(
        id=embedding_id,
        chunk_id=embedding.chunk_id,
        vector=embedding.vector,
        created_at=datetime.utcnow(),
        paper_id=embedding.paper_id,
    )


# Get all embeddings
@router.get("/", response_model=List[Embedding])
async def read_embeddings():
    query = select(models.Embedding)
    rows = await database.fetch_all(query)
    return rows


# Get an embedding by ID
@router.get("/{embedding_id}", response_model=Embedding)
async def read_embedding(embedding_id: uuid.UUID):
    query = select(models.Embedding).where(models.Embedding.id == embedding_id)
    embedding = await database.fetch_one(query)
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return embedding


# Update an embedding
@router.put("/{embedding_id}", response_model=Embedding)
async def update_embedding(embedding_id: uuid.UUID, updated_embedding: EmbeddingCreate):
    # Check if the embedding exists
    query = select(models.Embedding).where(models.Embedding.id == embedding_id)
    embedding = await database.fetch_one(query)
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    # Check if the paper exists
    query = select(models.Paper).where(models.Paper.id == updated_embedding.paper_id)
    paper = await database.fetch_one(query)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    q = (
        update(models.Embedding)
        .where(models.Embedding.id == embedding_id)
        .values(
            chunk_id=updated_embedding.chunk_id,
            vector=updated_embedding.vector,
            paper_id=updated_embedding.paper_id,
        )
    )
    await database.execute(q)

    return Embedding(
        id=embedding_id,
        chunk_id=updated_embedding.chunk_id,
        vector=updated_embedding.vector,
        created_at=embedding["created_at"],
        paper_id=updated_embedding.paper_id,
    )


# Delete an embedding
@router.delete("/{embedding_id}")
async def delete_embedding(embedding_id: uuid.UUID):
    query = select(models.Embedding).where(models.Embedding.id == embedding_id)
    embedding = await database.fetch_one(query)
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")

    q = delete(models.Embedding).where(models.Embedding.id == embedding_id)
    await database.execute(q)

    return {"message": "Embedding deleted successfully"}
