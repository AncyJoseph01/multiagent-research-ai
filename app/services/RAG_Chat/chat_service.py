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
from sqlalchemy import select

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
gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")


# ----------------------------- LLM Helper -----------------------------
async def _call_gemini(prompt: str, temperature: float = 0.3) -> str:
    """Call Gemini API asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: gemini_model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 4000}
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
    Uses keyword-based relevance check and limits to top 3 papers to conserve quota.
    Implements rate limiting to stay under API limits (100/min for embeddings, 20/day for generation).
    """
    added_papers = []

    # Define keywords to check relevance
    RELEVANT_KEYWORDS = ["transformer", "attention", "bert", "gpt", "llm", "longformer", "sparse", "routing", "language model"]

    for identifier in identifiers[:3]:  # Limit to top 3 papers to conserve API quota
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

            # Avoid duplicates (check if arxiv_id already exists for this user)
            if paper_info.get("arxiv_id"):
                existing = await database.fetch_one(
                    select(Paper.id).where(
                        (Paper.arxiv_id == paper_info["arxiv_id"]) & (Paper.user_id == user_id)
                    )
                )
                if existing:
                    logger.info(f"Paper already exists: {paper_info['title']}")
                    continue

            # Download PDF and extract text
            pdf_content = await arxiv_service.download_pdf_content(paper_info["pdf_url"])
            if not pdf_content:
                logger.warning(f"Could not download PDF: {paper_info['arxiv_id']}")
                continue

            text = pdf_service.extract_pdf_text(pdf_content)
            chunks = pdf_service.split_text_into_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

            # Optional similarity check with rate limiting to avoid quota burn
            if query_vector:
                chunk_embeddings = []
                for c in chunks[:3]:  # Only check first 3 chunks
                    try:
                        emb = embedding_service.create_embedding(c)
                        chunk_embeddings.append(emb)
                        await asyncio.sleep(0.65)  # Rate limit: ~100 requests/min
                    except Exception as e:
                        logger.warning(f"Could not embed chunk for similarity check: {e}")
                        await asyncio.sleep(0.65)
                        continue
                
                sims = [
                    float(np.dot(query_vector, np.array(e)) /
                          (np.linalg.norm(query_vector) * np.linalg.norm(e)))
                    for e in chunk_embeddings if e is not None
                ]
                if not sims or max(sims) < SIMILARITY_THRESHOLD:
                    logger.info(f"Paper failed similarity check: {paper_info['title']} (max sim {max(sims) if sims else 0})")
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
    - Now includes conversation history for context awareness
    """
    logger.info(f"Query received: {query} | use_cot={use_cot} | user_id={user_id}")
    
    # Verify user has papers
    try:
        if isinstance(user_id, str):
            user_uuid = uuid.UUID(user_id)
        else:
            user_uuid = user_id
        
        papers_count = await database.fetch_val(
            "SELECT COUNT(*) FROM papers WHERE user_id = :user_id",
            {"user_id": user_uuid}
        )
        logger.info(f"User has {papers_count} papers in database")
    except Exception as e:
        logger.error(f"Error checking user papers: {e}")
    
    query_vector = embedding_service.create_embedding(query)
    logger.debug(f"Query vector sample: {query_vector[:5]}...")

    # ========== FETCH ALL USER PAPERS ==========
    all_papers = await database.fetch_all(
        select(Paper.id, Paper.title, Paper.authors, Paper.abstract, Paper.arxiv_id).where(Paper.user_id == user_uuid)
    )
    papers_list = "\n".join([
        f"- **{p['title']}** by {p['authors'] or 'Unknown'}" + (f" (arXiv: {p['arxiv_id']})" if p['arxiv_id'] else "")
        for p in all_papers
    ])
    papers_context = f"**User's Papers Summary:** You have access to {len(all_papers)} paper(s).\n\n**User's Uploaded Papers:**\n{papers_list}\n\n" if papers_list else "**User's Papers Summary:** You have access to 0 papers.\n\n"
    logger.debug(f"Found {len(all_papers)} user papers")

    # ========== FETCH CONVERSATION HISTORY ==========
    chat_history_rows = await database.fetch_all(
        Chat.__table__.select().where(Chat.chat_session_id == session_id).order_by(Chat.created_at.asc())
    )
    conversation_history = "\n".join([
        f"User: {row['query']}\nAssistant: {row['answer'][:500]}..." if len(row['answer']) > 500 else f"User: {row['query']}\nAssistant: {row['answer']}"
        for row in chat_history_rows[-5:]  # Last 5 messages for context
    ])
    history_context = f"PREVIOUS CONVERSATION:\n{conversation_history}\n\n" if conversation_history else ""

    # Initial RAG retrieval
    relevant_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
    context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in relevant_chunks])
    logger.info(f"Retrieved {len(relevant_chunks)} chunks from RAG")
    
    # ⚠️ CRITICAL: Warn if no context available from RAG
    if not relevant_chunks:
        logger.warning(f"⚠️ WARNING: No embeddings/chunks retrieved! User papers may not have embeddings created yet, or they may still be processing.")
        logger.warning(f"⚠️ LLM will respond from general knowledge WITHOUT access to user's papers!")

    cot_transcript = None

    if use_cot:
        # CoT stages - run sequentially to use outputs from prior stages
        
        # Stage 1: Exploration
        exploration_prompt = (
            f"STAGE: Exploration - Initial Analysis\n\n"
            f"User Query: {query}\n"
            f"User's Papers: {len(all_papers)} papers available\n"
            f"Papers: {papers_list}\n\n"
            f"Task: Identify what you know and what you don't know.\n"
            f"- What is the USER'S SPECIFIC LEARNING GOAL or REQUEST? (extract explicitly)\n"
            f"- What concepts/topics are they asking about?\n"
            f"- What information is available in their {len(all_papers)} papers?\n"
            f"- What key gaps exist in knowledge? (limit to 2-3)\n\n"
            f"Keep it brief (150 words max)."
        )
        exploration_text = await _call_gemini(exploration_prompt, temperature=0.5)

        # Stage 2: Draft
        draft_prompt = (
            f"STAGE: Draft - Strategy to Address the User's Goal\n\n"
            f"User Query: {query}\n"
            f"Context (from user's papers):\n{context_text}\n\n"
            f"Task: Outline your approach.\n"
            f"- How the user's current papers relate to their query\n"
            f"- Main topics/concepts to cover (numbered list)\n"
            f"- Which user papers are most relevant?\n"
            f"- What types of papers/knowledge are missing?\n\n"
            f"Keep it brief (150 words max)."
        )
        draft_text = await _call_gemini(draft_prompt, temperature=0.5)

        # Stage 3: Reflection - Suggests papers to fetch
        reflection_prompt = (
            f"STAGE: Reflection - Critical Evaluation & Paper Suggestions\n\n"
            f"User Query: {query}\n"
            f"Context (from user's papers):\n{context_text}\n\n"
            f"Task: Identify limitations and suggest specific papers to fill gaps.\n"
            f"For each paper suggestion, explain:\n"
            f"- WHY it's relevant to the user's query\n"
            f"- WHAT specific aspect it covers that's missing from current papers\n"
            f"- HOW it will help achieve the user's stated goal\n\n"
            f"Format: For each paper, provide on separate lines:\n"
            f"REASON: [Why this paper]\n"
            f"IDENTIFIER: [arXiv ID like 2301.12345 OR TITLE: paper name]\n\n"
            f"Suggest 2-3 papers maximum.\n"
            f"Keep it brief (200 words max)."
        )
        reflection_text = await _call_gemini(reflection_prompt, temperature=0.5)
        
        # Extract and fetch suggested papers
        suggested_identifiers = await _extract_arxiv_ids_or_titles(reflection_text)
        new_papers_data = []
        
        if suggested_identifiers:
            new_papers = await _fetch_and_process_papers(suggested_identifiers, user_id, query_vector)
            logger.info(f"New papers added: {new_papers}")
            
            # Fetch details of newly added papers for reference in synthesis
            for paper_id in new_papers:
                paper_info = await database.fetch_one(
                    select(Paper.title, Paper.abstract, Paper.arxiv_id, Paper.authors).where(Paper.id == paper_id)
                )
                if paper_info:
                    new_papers_data.append({
                        "id": paper_id,
                        "title": paper_info['title'],
                        "arxiv_id": paper_info['arxiv_id'],
                        "authors": paper_info['authors']
                    })
            
            # Refresh context with new papers
            if new_papers:
                new_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
                context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in new_chunks])
                logger.info(f"Context updated with {len(new_chunks)} chunks including new papers")
        
        new_papers_list = "\n".join([
            f"- **{p['title']}** (arXiv: {p['arxiv_id']}) by {p['authors'] or 'Unknown'}"
            for p in new_papers_data
        ]) if new_papers_data else "No new papers added."

        # Stage 4: Synthesis - Final answer with updated context
        synthesis_prompt = (
            f"STAGE: Synthesis - Final Comprehensive Answer\n\n"
            f"User Query: {query}\n"
            f"Context (from user's papers, including newly added ones):\n{context_text}\n\n"
            f"NEWLY ADDED PAPERS TO EXPLAIN:\n{new_papers_list}\n\n"
            f"Task: Provide a clear, well-structured answer incorporating all available papers.\n"
            f"CRITICAL: If new papers were added:\n"
            f"1. Explicitly state which papers were added and why (reference the reasons from Reflection)\n"
            f"2. Explain how each new paper helps address the user's specific learning goal\n"
            f"3. Connect the new papers to the user's core request\n\n"
            f"Format requirements:\n"
            f"- Use Markdown format\n"
            f"- Have a clear section introducing newly added papers and their relevance\n"
            f"- Reference papers by title and arXiv ID\n"
            f"- Distinguish between user's originally uploaded papers and newly suggested papers\n"
            f"- Address the query directly and comprehensively"
        )
        synthesis_text = await _call_gemini(synthesis_prompt, temperature=0.3)
        
        # Build detailed transcript with paper selection reasoning
        reflection_with_papers = f"{reflection_text}\n\n**Papers Added:**\n{new_papers_list}"
        
        stage_dict = {
            "Exploration": exploration_text,
            "Draft": draft_text,
            "Reflection": reflection_with_papers,
            "Synthesis": synthesis_text
        }
        cot_transcript = "\n\n".join([f"## {s}\n{stage_dict[s]}" for s in ["Exploration", "Draft", "Reflection", "Synthesis"]])
        final_answer = synthesis_text

    else:
        # RAG-only mode
        final_prompt = (
            f"{papers_context}"
            f"{history_context}"
            f"User Query: {query}\n"
            f"Context (from user's uploaded papers):\n{context_text}\n"
            f"Instructions:\n"
            f"- Provide a structured Markdown answer based on the user's papers.\n"
            f"- If the context mentions other papers/statistics, clearly distinguish:\n"
            f"  1. The user's uploaded papers (these are their direct access)\n"
            f"  2. Papers/studies mentioned WITHIN those documents (reference as 'cited in' or 'discussed in').\n"
            f"- Do NOT claim the user has access to papers they didn't upload.\n"
            f"- Remember previous papers discussed in this conversation."
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