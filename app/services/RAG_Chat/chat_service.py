"""
Agentic Research Assistant:
- Multi-stage reasoning pipeline: Exploration → Draft → Reflection → Synthesis.
- Suggests relevant arXiv papers automatically, using both IDs and titles.
- Fetches PDFs, extracts text, splits into chunks, and generates embeddings.
- Dynamically updates retrieval context (RAG) with newly added papers.
- Produces structured, Markdown-formatted academic answers with references.
- Fully asynchronous and FastAPI-compatible for scalable, responsive queries.
- Optional Chain-of-Thought (CoT) mode for deeper reasoning and incremental insight.
- Built-in similarity filtering ensures only relevant papers are added.
- Maintains logs and transcripts of reasoning stages for transparency and debugging.
"""

import uuid
import re
import os
import logging
from typing import List
from datetime import datetime
import asyncio
import numpy as np

from app.db.models import Chat, Paper, Summary
from app.db.database import database
from app.services.research_assistant import (
    embedding_service,
    pdf_service,
    arxiv_service,
    summariser_service
)
from app.services.RAG_Chat import retrieval_service
import google.generativeai as genai

# ----------------------------- Logger -----------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# ----------------------------- Config -----------------------------
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
SIMILARITY_THRESHOLD = 0.60

# ----------------------------- Gemini Setup -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not set")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")

# ----------------------------- LLM Helper -----------------------------
async def _call_gemini(prompt: str, temperature: float = 0.3) -> str:
    """Call Gemini API asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: gemini_model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 1200}
        ).text.strip()
    )

# ----------------------------- Extract arXiv IDs / Titles -----------------------------
async def _extract_arxiv_ids_or_titles(text: str) -> List[str]:
    """
    Extract valid arXiv IDs and titles explicitly marked with TITLE:
    Example output from LLM:
      2301.12345
      TITLE: Longformer: The Long-Document Transformer
    """
    ids = re.findall(r'\b(\d{4}\.\d{4,5}|[a-zA-Z\-\.]+/\d{7})\b', text)
    titles = re.findall(r'TITLE:\s*["“”]?(.+?)["“”]?(?:\n|$)', text)
    identifiers = list(set(ids + titles))
    logger.info(f"Identifiers extracted for fetching: {identifiers}")
    return identifiers

# ----------------------------- Fetch & Process Papers -----------------------------
async def _fetch_and_process_papers(
    identifiers: List[str],
    user_id: str,
    query_vector: list[float] = None
) -> List[str]:
    """
    Fetch papers from arXiv, extract text, generate embeddings, save to DB.
    Uses keyword-based relevance check instead of strict categories.
    """
    added_papers = []

    # Define keywords to check relevance
    RELEVANT_KEYWORDS = ["transformer", "attention", "bert", "gpt", "llm", "longformer", "sparse", "routing", "language model"]

    for identifier in identifiers[:5]:  # Limit top 5 suggestions for speed
        logger.info(f"Fetching paper: {identifier}")
        papers = []

        # Detect arXiv ID
        if re.match(r'^\d{4}\.\d{4,5}$', identifier) or re.match(r'^[a-zA-Z\-\.]+/\d{7}$', identifier):
            papers = arxiv_service.fetch_arxiv_papers(identifier, max_results=1)
        else:
            papers = arxiv_service.fetch_arxiv_papers(identifier, max_results=1)

        if not papers:
            logger.warning(f"No papers found for {identifier}")
            continue

        for paper_info in papers:
            # Keyword-based relevance check
            text_to_check = (paper_info.get("title","") + " " + paper_info.get("abstract","")).lower()
            if not any(kw in text_to_check for kw in RELEVANT_KEYWORDS):
                logger.info(f"Skipping paper not matching keywords: {paper_info['title']}")
                continue

            # Avoid duplicates
            existing = await database.fetch_one(
                Paper.__table__.select().where(
                    (Paper.arxiv_id == paper_info["arxiv_id"]) & (Paper.user_id == user_id)
                )
            )
            if existing:
                continue

            # Download PDF and extract text
            pdf_content = await arxiv_service.download_pdf_content(paper_info["pdf_url"])
            if not pdf_content:
                continue

            text = pdf_service.extract_pdf_text(pdf_content)
            chunks = pdf_service.split_text_into_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

            # Optional similarity check
            if query_vector:
                chunk_embeddings = [embedding_service.create_embedding(c) for c in chunks[:3]]
                sims = [
                    float(np.dot(query_vector, np.array(e)) /
                          (np.linalg.norm(query_vector) * np.linalg.norm(e)))
                    for e in chunk_embeddings if e is not None
                ]
                if not sims or max(sims) < SIMILARITY_THRESHOLD:
                    logger.info(f"Paper failed similarity: {paper_info['title']} (max sim {max(sims) if sims else 0})")
                    continue

            # Save paper to DB
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

            # Summarise
            summary_text = summariser_service.summarise_text(
                text, title=paper_info["title"], authors=paper_info["authors"], arxiv_id=paper_info["arxiv_id"]
            )
            await database.execute(Summary.__table__.insert().values({
                "id": uuid.uuid4(),
                "paper_id": paper_id,
                "summary_type": "structured",
                "content": summary_text,
                "created_at": datetime.utcnow()
            }))

            # Save embeddings
            await embedding_service.create_and_save_embeddings(paper_id, chunks)

            # Mark paper as done
            await database.execute(
                Paper.__table__.update().where(Paper.id == paper_id).values(status="done")
            )
            added_papers.append(paper_id)
            logger.info(f"Paper added: {paper_info['title']}")

    return added_papers


# ----------------------------- Main Agentic Function -----------------------------
async def ask_research_assistant(
    user_id: str,
    query: str,
    session_id: int,
    use_cot: bool = False
) -> dict:
    """
    Agentic Research Assistant:
    - RAG + optional CoT + auto arXiv fetching
    """
    logger.info(f"Query received: {query} | use_cot={use_cot}")
    query_vector = embedding_service.create_embedding(query)
    logger.debug(f"Query vector sample: {query_vector[:5]}...")

    # Initial RAG retrieval
    relevant_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
    context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in relevant_chunks])
    logger.info(f"Retrieved {len(relevant_chunks)} chunks from RAG")

    cot_transcript = None

    if use_cot:
        # CoT stages
        stages = ["Exploration", "Draft", "Reflection", "Synthesis"]

        async def _run_stage(stage):
            prompt = (
        f"INTERNAL REASONING MODE [{stage}]\n"
        f"User Query: {query}\n"
        f"Context:\n{context_text}\n\n"
        f"Instructions:\n"
        f"- Think deeply about the query.\n"
        f"- Identify gaps, limitations, and key insights.\n"
        f"- Suggest relevant arXiv papers.\n"
        f"- When possible, output exact arXiv IDs (format: 2403.12345).\n"
        f"- If IDs are not available, prefix titles with 'TITLE:'.\n"
        f"- Focus on structuring knowledge for academic output.\n"
        f"- Include your reasoning/thought process in brackets or markdown.\n"
        f"- Clearly separate reasoning from final suggestions for easy parsing.\n\n"
        f"Format example:\n"
        f"[Reasoning: Explain why these papers are relevant...]\n"
        f"Suggested papers:\n"
        f"2301.12345\n"
        f"TITLE: Example Paper Title"
    )
            return await _call_gemini(prompt)


        stage_texts = await asyncio.gather(*[_run_stage(stage) for stage in stages])
        stage_dict = dict(zip(stages, stage_texts))
        cot_transcript = "\n\n".join([f"## {s}\n{stage_dict[s]}" for s in stages])

        # Extract suggested papers from Reflection + Synthesis
        suggested_identifiers = await _extract_arxiv_ids_or_titles(
            stage_dict["Reflection"] + "\n" + stage_dict["Synthesis"]
        )
        new_papers = await _fetch_and_process_papers(suggested_identifiers, user_id, query_vector) if suggested_identifiers else []
        logger.info(f"New papers added: {new_papers}")

        # Refresh context with new papers
        if new_papers:
            new_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
            context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in new_chunks])
            logger.info(f"Context updated with {len(new_chunks)} chunks including new papers")

        # Final structured answer
        final_prompt = (
            f"EXIT INTERNAL REASONING MODE\n"
            f"User Query: {query}\n"
            f"Context (including new papers):\n{context_text}\n"
            f"Instructions: Produce a structured academic answer in Markdown."
        )
        final_answer = await _call_gemini(final_prompt)

    else:
        # RAG-only mode
        final_prompt = (
            f"User Query: {query}\n"
            f"Context:\n{context_text}\n"
            f"Instructions: Provide structured Markdown answer."
        )
        final_answer = await _call_gemini(final_prompt)

    # Save chat
    await database.execute(Chat.__table__.insert().values({
        "id": uuid.uuid4(),
        "chat_session_id": session_id,
        "query": query,
        "answer": final_answer,
        "cot_transcript": cot_transcript,
        "user_id": user_id,
        "created_at": datetime.utcnow()
    }))
    logger.info(f"Chat saved for session {session_id}")

    return {"answer": final_answer, "cot_transcript": cot_transcript}