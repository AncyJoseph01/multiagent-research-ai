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
    Extract both arXiv IDs and suggested paper titles from the LLM output.
    """
    # Find explicit arXiv IDs
    ids = re.findall(r'arXiv[:\s]?(\d{4}\.\d{4,5})', text)
    
    # Heuristic: extract suggested titles (e.g., lines starting with dash)
    titles = re.findall(r'-\s(.+)', text)
    
    # Remove duplicates
    identifiers = list(set(ids + titles))
    return identifiers


# -----------------------------
# Helper: Fetch & process papers
# -----------------------------
async def _fetch_and_process_papers(papers_identifiers: List[str], user_id: str):
    for identifier in papers_identifiers:
        # Skip if already exists (by ID or title)
        existing = await database.fetch_one(
            Paper.__table__.select().where(
                (Paper.arxiv_id == identifier) | (Paper.title.ilike(f"%{identifier}%"))
            ).where(Paper.user_id == user_id)
        )
        if existing:
            continue

        # Fetch paper(s) from arXiv
        papers = arxiv_service.fetch_arxiv_papers(identifier, max_results=2)  # max_results>1 for title search
        if not papers:
            continue

        for paper_info in papers:
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
- Suggest relevant arXiv papers (IDs or titles).
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

# """
# Agentic Research Assistant:
# - high-level agentic orchestration
# - Multi-stage Chain-of-Thought reasoning (Exploration → Draft → Reflection → Synthesis)
# - Similarity search from user's stored embeddings
# - Detects relevant arXiv papers, auto-fetches + processes + embeds them
# - Produces final structured answer
# - Async-compatible for FastAPI
# """

# import uuid
# import re
# import os
# import logging

# from typing import List
# from datetime import datetime

# from app.db.models import Chat, Paper
# from app.db.database import database
# from app.services.research_assistant import (

#     embedding_service,
#     pdf_service,
#     arxiv_service,
#     summariser_service
# )
# from app.services.RAG_Chat import retrieval_service
# import google.generativeai as genai
# from app.core.config import settings  # Your GEMINI_API_KEY location

# CHUNK_SIZE = 1000     
# CHUNK_OVERLAP = 200      
# TOP_K = 5  

# logger = logging.getLogger(__name__)

# # -----------------------------
# # Gemini SDK Setup
# # -----------------------------
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if not GEMINI_API_KEY:
#     logger.error("Gemini API key not set in .env file")
#     raise ValueError("Gemini API key not set in .env file")

# try:
#     genai.configure(api_key=GEMINI_API_KEY)
#     gemini_model = genai.GenerativeModel("gemini-1.5-pro")
# except Exception as e:
#     logger.error(f"Failed to initialize Gemini client: {e}")
#     raise


# # -----------------------------
# # LLM Helpers
# # -----------------------------
# def _call_gemini(prompt: str, temperature: float = 0.4):
#     """
#     Generate content using Gemini SDK.
#     """
#     response = gemini_model.generate_content(
#         prompt,
#         generation_config={
#             "temperature": temperature,
#             "max_output_tokens": 1000,
#         }
#     )
#     return response


# def _extract_text(response) -> str:
#     """
#     Extract text from Gemini SDK response.
#     """
#     return response.text.strip() if response and response.text else ""



# # -----------------------------
# # Helper: Extract & verify arXiv IDs
# # -----------------------------
# async def _extract_verified_arxiv_ids(text: str) -> List[str]:
#     potential_ids = re.findall(r'arXiv[:\s]?(\d{4}\.\d{4,5})', text)
#     verified_ids = []
#     for arxiv_id in potential_ids:
#         try:
#             papers = arxiv_service.fetch_arxiv_papers(arxiv_id, max_results=1)
#             if papers and papers[0]["arxiv_id"] == arxiv_id:
#                 verified_ids.append(arxiv_id)
#         except Exception:
#             continue
#     return verified_ids

# # -----------------------------
# # Helper: Fetch & process arXiv papers from CoT text
# # -----------------------------
# async def _fetch_and_process_arxiv_papers_from_text(cot_text: str, user_id: str):
#     arxiv_ids = await _extract_verified_arxiv_ids(cot_text)
#     if not arxiv_ids:
#         return
#     await _fetch_and_process_arxiv_papers(arxiv_ids, user_id)

# # -----------------------------
# # Helper: Fetch & process arXiv papers
# # -----------------------------
# async def _fetch_and_process_arxiv_papers(arxiv_ids: List[str], user_id: str):
#     for arxiv_id in arxiv_ids:
#         existing_query = await database.fetch_one(
#             Paper.__table__.select().where(Paper.arxiv_id == arxiv_id).where(Paper.user_id == user_id)
#         )
#         if existing_query:
#             continue

#         papers = arxiv_service.fetch_arxiv_papers(arxiv_id, max_results=1)
#         if not papers:
#             continue
#         paper_info = papers[0]

#         pdf_content = await arxiv_service.download_pdf_content(paper_info["pdf_url"])
#         if not pdf_content:
#             continue

#         text = pdf_service.extract_pdf_text(pdf_content)

#         paper_id = uuid.uuid4()
#         await database.execute(Paper.__table__.insert().values({
#             "id": paper_id,
#             "title": paper_info["title"],
#             "abstract": paper_info["abstract"],
#             "authors": paper_info["authors"],
#             "arxiv_id": paper_info["arxiv_id"],
#             "url": paper_info["url"],
#             "published_at": paper_info["published_at"],
#             "user_id": user_id,
#             "status": "pending",
#             "created_at": datetime.utcnow()
#         }))

#         summary_text = summariser_service.summarise_text(
#             text,
#             title=paper_info["title"],
#             authors=paper_info["authors"],
#             arxiv_id=arxiv_id
#         )
#         await database.execute(summariser_service.Summary.__table__.insert().values({
#             "id": uuid.uuid4(),
#             "paper_id": paper_id,
#             "summary_type": "structured",
#             "content": summary_text,
#             "created_at": datetime.utcnow()
#         }))

#         chunks = pdf_service.split_text_into_chunks(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
#         await embedding_service.create_and_save_embeddings(paper_id, chunks)

#         await database.execute(
#             Paper.__table__.update()
#             .where(Paper.id == paper_id)
#             .values(status="done")
#         )

# # -----------------------------
# # Helper: Simple regex extract
# # -----------------------------
# def _extract_arxiv_ids(text: str) -> List[str]:
#     return re.findall(r'arXiv[:\s]?(\d{4}\.\d{4,5})', text)

# # -----------------------------
# # Main agentic function
# # -----------------------------

# GREETING_KEYWORDS = ["hello", "hi", "hey", "who are you", "introduce yourself"]

# async def ask_research_assistant(user_id: str, query: str, session_id: int) -> dict:
#     # 1️⃣ Query embedding
#     query_vector = embedding_service.create_embedding(query)

#     # 2️⃣ Retrieve relevant chunks
#     relevant_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
#     context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in relevant_chunks])

#     # 3️⃣ Multi-stage CoT
#     stages = ["Exploration", "Draft", "Reflection", "Synthesis"]
#     stage_texts = {}

#     for stage in stages:
#         prompt = f"""
# INTERNAL REASONING MODE [{stage}]
# User Query: {query}

# Context from relevant papers:
# {context_text}

# Instructions:
# - Think deeply and systematically.
# - Focus on how to answer the research question.
# - Identify missing connections, strengths, and limitations.
# - Suggest related papers from arXiv or user history if useful.
# """
#         resp = _call_gemini(prompt)
#         stage_texts[stage] = _extract_text(resp)

#     # 4️⃣ Auto-fetch verified arXiv papers
#     await _fetch_and_process_arxiv_papers_from_text(stage_texts["Synthesis"], user_id)
#     new_chunks = await retrieval_service.retrieve_similar_chunks(query_vector, user_id, top_k=TOP_K)
#     context_text = "\n\n".join([f"Paper {c['paper_id']} summary:\n{c['summary']}" for c in new_chunks])

#     # 5️⃣ Final user-facing answer
#     final_prompt = f"""
# EXIT INTERNAL REASONING MODE

# User Query: {query}

# Internal reasoning:
# - Exploration: {stage_texts['Exploration']}
# - Draft: {stage_texts['Draft']}
# - Reflection: {stage_texts['Reflection']}
# - Synthesis: {stage_texts['Synthesis']}

# Produce a final structured academic answer:
# - Include insights from retrieved papers
# - Suggest related papers if useful
# - Highlight gaps or improvements
# - Format in Markdown
# """
#     final_resp = _call_gemini(final_prompt)
#     final_answer = _extract_text(final_resp)

#     # 6️⃣ CoT transcript
#     cot_transcript = "\n\n".join([f"## {stage}\n{stage_texts[stage]}" for stage in stages])

#     # 7️⃣ Save chat
#     chat_data = {
#         "id": uuid.uuid4(),
#         "chat_session_id": session_id,
#         "query": query,
#         "answer": final_answer,
#         "cot_transcript": cot_transcript,
#         "user_id": user_id,
#         "created_at": datetime.utcnow()
#     }
#     await database.execute(Chat.__table__.insert().values(chat_data))

#     return {"answer": final_answer, "cot_transcript": cot_transcript}
