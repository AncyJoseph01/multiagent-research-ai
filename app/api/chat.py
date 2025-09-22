from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.db.database import database
from app.db import models
from app.schema import chat as chat_schema
from app.services.RAG_Chat.chat_service import ask_research_assistant
from datetime import datetime
router = APIRouter()


# Ask assistant
@router.post("/", response_model=chat_schema.ChatResponse)
async def ask_chat(req: chat_schema.ChatRequest, user_id: str):
    session_id = req.chat_session_id or int(datetime.utcnow().timestamp())

    result = await ask_research_assistant(
        user_id=user_id,
        query=req.query,
        session_id=session_id,
        use_cot=req.use_cot or False,
    )

    query = (
        models.Chat.__table__
        .select()
        .where(models.Chat.chat_session_id == session_id)
        .order_by(models.Chat.created_at.desc())
    )
    row = await database.fetch_one(query)

    if not row:
        raise HTTPException(status_code=500, detail="Chat not saved")

    return chat_schema.ChatResponse(
        id=row.id,
        chat_session_id=row.chat_session_id,
        user_id=row.user_id,
        query=row.query,
        answer=row.answer,
        created_at=row.created_at or datetime.utcnow(),  # fallback
    )


# Get chat history for one session
@router.get("/history/{session_id}", response_model=chat_schema.ChatHistory)
async def get_chat_history(session_id: int, user_id: str):
    query = (
        models.Chat.__table__
        .select()
        .where(models.Chat.chat_session_id == session_id)
        .where(models.Chat.user_id == user_id)
        .order_by(models.Chat.created_at.asc())
    )
    rows = await database.fetch_all(query)

    chats = [
        chat_schema.ChatResponse(
            id=row.id,
            chat_session_id=row.chat_session_id,
            user_id=row.user_id,
            query=row.query,
            answer=row.answer,
            cot_transcript=row.cot_transcript,
            created_at=row.created_at or datetime.utcnow(),  # fallback
        )
        for row in rows
    ]

    return chat_schema.ChatHistory(chat_session_id=session_id, chats=chats)


# List all sessions for a user
@router.get("/sessions/{user_id}", response_model=list[chat_schema.ChatSessionInfo])
async def get_sessions(user_id: str):
    query = """
    SELECT c.chat_session_id,
           MAX(c.created_at) AS created_at,
           (ARRAY_AGG(c.query ORDER BY c.created_at DESC))[1] AS chat_query
    FROM chat c
    WHERE c.user_id = :user_id
    GROUP BY c.chat_session_id
    ORDER BY MAX(c.created_at) DESC;
    """
    rows = await database.fetch_all(query, {"user_id": user_id})
    return [
        chat_schema.ChatSessionInfo(
            chat_session_id=row["chat_session_id"],
            created_at=row["created_at"] or datetime.utcnow(),
            chat_query=row["chat_query"] or "",
        )
        for row in rows
    ]

