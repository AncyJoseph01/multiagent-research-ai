"""
Agentic Research Assistant:
- Multi-stage reasoning (Exploration → Draft → Reflection → Synthesis)
- Auto-fetches related arXiv papers (by ID or title)
- Processes PDFs, generates embeddings, refreshes retrieval
- Produces structured academic answers
- Async-compatible for FastAPI
"""

import uuid
import re
import os
import logging
from typing import List
from datetime import datetime

from app.db.models import Chat, Paper, Summary, Embedding
from app.db.database import database
from app.services.research_assistant import (
    embedding_service,
    pdf_service,
    arxiv_service,
    summariser_service
)
from app.services.RAG_Chat import retrieval_service
import google.generativeai as genai

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5

# -----------------------------
# Gemini Setup
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not set")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-pro")

# -----------------------------
# LLM helpers
# -----------------------------
def _call_gemini(prompt: str, temperature: float = 0.3) -> str:
    response = gemini_model.generate_content(
        prompt,
        generation_config={"temperature": temperature, "max_output_tokens": 1200}
    )
    return response.text.strip() if response and response.text else ""


# -----------------------------
# Helper: Extract arXiv IDs or Titles
# -----------------------------
async def _extract_arxiv_ids_or_titles(text: str) -> List[str]:
    """
    Extract both arXiv IDs (modern + legacy) and suggested paper titles from the LLM output.
    """
    # Modern IDs: 2301.12345
    # Legacy IDs: cs.AI/0301001
    ids = re.findall(r'arXiv[:\s]?([a-zA-Z\-\.]+/\d{7}|\d{4}\.\d{4,5})', text)

    # Titles (lines starting with -, •, *, or prefixed with TITLE:)
    titles = re.findall(r'(?:-|\*|•|TITLE:)\s+["“”]?(.+?)["“”]?(?:\n|$)', text)

    identifiers = list(set(ids + titles))
    return identifiers


# -----------------------------
# Helper: Fetch & process papers
# -----------------------------
async def _fetch_and_process_papers(papers_identifiers: List[str], user_id: str):
    for identifier in papers_identifiers:
        papers = []

        # Detect if identifier looks like an arXiv ID
        if re.match(r'^\d{4}\.\d{4,5}$', identifier) or re.match(r'^[a-zA-Z\-\.]+/\d{7}$', identifier):
            # Fetch by arXiv ID (exact)
            paper_info = arxiv_service.fetch_arxiv_paper_by_id(identifier)
            if paper_info:
                papers = [paper_info]
        else:
            # Otherwise treat as keyword / title search
            papers = arxiv_service.fetch_arxiv_papers(identifier, max_results=2)

        if not papers:
            continue

        for paper_info in papers:
            # Skip if already exists (check by canonical arXiv ID)
            existing = await database.fetch_one(
                Paper.__table__.select().where(
                    (Paper.arxiv_id == paper_info["arxiv_id"]) & (Paper.user_id == user_id)
                )
            )
            if existing:
                continue

            pdf_content = await arxiv_service.download_pdf_content(paper_info["pdf_url"])
            if not pdf_content:
                continue

            text = pdf_service.extract_pdf_text(pdf_content)
            paper_id = uuid.uuid4()

            await database.execute(Paper.__table__.insert().values({
                "id": paper_id,
                "title": paper_info["title"],
                "abstract": paper_info["abstract"],
                "authors": paper_info["authors"],
                "arxiv_id": paper_info["arxiv_id"],
                "url": paper_info["url"],
                "published_at": paper_info["published_at"],
                "user_id": user_id,
                "status": "pending",
                "created_at": datetime.utcnow()
            }))

            summary_text = summariser_service.summarise_text(
                text,
                title=paper_info["title"],
                authors=paper_info["authors"],
                arxiv_id=paper_info["arxiv_id"]
            )
            await database.execute(Summary.__table__.insert().values({
                "id": uuid.uuid4(),
                "paper_id": paper_id,
                "summary_type": "structured",
                "content": summary_text,
                "created_at": datetime.utcnow()
            }))

            chunks = pdf_service.split_text_into_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)
            await embedding_service.create_and_save_embeddings(paper_id, chunks)

            await database.execute(
                Paper.__table__.update().where(Paper.id == paper_id).values(status="done")
            )


# -----------------------------
# Main agentic function
# -----------------------------
async def ask_research_assistant(user_id: str, query: str, session_id: int) -> dict:
    """
    Multi-stage research assistant that fetches related papers, generates embeddings,
    and produces structured academic answers.
    """
    # 1️⃣ Embed query
    query_vector = embedding_service.create_embedding(query)

    # 2️⃣ Retrieve initial relevant chunks
    relevant_chunks = await retrieval_service.retrieve_similar_chunks(
        query_vector, user_id, top_k=TOP_K
    )
    context_text = "\n\n".join(
        [f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in relevant_chunks]
    )

    # 3️⃣ Multi-stage CoT reasoning
    stages = ["Exploration", "Draft", "Reflection", "Synthesis"]
    stage_texts = {}

    for stage in stages:
        prompt = f"""
INTERNAL REASONING MODE [{stage}]
User Query: {query}

Context from retrieved papers:
{context_text}

Instructions:
- Think deeply about the query.
- Identify gaps, limitations, and key insights.
- Suggest relevant arXiv papers.
- When possible, output exact arXiv IDs (format: 2403.12345).
- If IDs are not available, prefix titles with "TITLE:".
- Focus on structuring knowledge for academic output.
"""
        stage_texts[stage] = _call_gemini(prompt)

    # 4️⃣ Extract suggested IDs/titles from Reflection + Synthesis
    suggested_identifiers = await _extract_arxiv_ids_or_titles(
        stage_texts["Reflection"] + "\n" + stage_texts["Synthesis"]
    )

    # 5️⃣ Fetch, process, embed new papers if any
    if suggested_identifiers:
        await _fetch_and_process_papers(suggested_identifiers, user_id)

        # Refresh retrieval after adding new papers
        new_chunks = await retrieval_service.retrieve_similar_chunks(
            query_vector, user_id, top_k=TOP_K
        )
        context_text = "\n\n".join(
            [f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in new_chunks]
        )

    # 6️⃣ Generate final structured answer
    final_prompt = f"""
EXIT INTERNAL REASONING MODE

User Query: {query}

Context from retrieved papers (including new arXiv papers):
{context_text}

Instructions:
- Produce structured academic answer in Markdown.
- Include key contributions, gaps, limitations.
- Reference relevant arXiv papers with summaries.
"""
    final_answer = _call_gemini(final_prompt)

    # 7️⃣ Combine CoT transcript
    cot_transcript = "\n\n".join([f"## {stage}\n{stage_texts[stage]}" for stage in stages])

    # 8️⃣ Save chat to DB
    await database.execute(Chat.__table__.insert().values({
        "id": uuid.uuid4(),
        "chat_session_id": session_id,
        "query": query,
        "answer": final_answer,
        "cot_transcript": cot_transcript,
        "user_id": user_id,
        "created_at": datetime.utcnow()
    }))

    return {"answer": final_answer, "cot_transcript": cot_transcript}
