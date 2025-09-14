"""
retrieval_service.py

Performs similarity search over stored embeddings (pgvector)
and returns relevant chunks and summaries for a given user query.
"""

from typing import List, Dict, Any
from sqlalchemy import select
from app.db.models import Embedding, Paper, Summary
from app.db.database import database
import numpy as np

TOP_K = 5  # number of similar chunks to retrieve

async def retrieve_similar_chunks(query_vector: list[float], user_id: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant chunks for a given query vector and user_id.
    Returns a list of dicts with:
        - chunk_id
        - paper_id
        - summary
        - similarity_score (cosine)
    """
    # 1️⃣ Fetch embeddings for user's papers
    query = (
        select(
            Embedding.id,
            Embedding.chunk_id,
            Embedding.paper_id,
            Embedding.vector,  # ✅ include the vector column
            Summary.content.label("summary_content")
        )
        .join(Paper, Paper.id == Embedding.paper_id)
        .outerjoin(Summary, Summary.paper_id == Paper.id)
        .where(Paper.user_id == user_id)
    )

    rows = await database.fetch_all(query)
    q_vec = np.array(query_vector)
    results = []

    # 2️⃣ Compute cosine similarity
    for row in rows:
        emb_vec = row["vector"]  # ✅ assign the vector here

        # Skip if embedding is None or shapes mismatch
        if emb_vec is None:
            continue

        emb_vec = np.array(emb_vec)
        if emb_vec.shape != q_vec.shape:
            continue

        similarity = float(np.dot(q_vec, emb_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(emb_vec)))

        results.append({
            "chunk_id": row["chunk_id"],
            "paper_id": row["paper_id"],
            "summary": row["summary_content"] or "",
            "similarity_score": similarity
        })

    # 3️⃣ Sort by similarity descending
    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return results[:top_k]
