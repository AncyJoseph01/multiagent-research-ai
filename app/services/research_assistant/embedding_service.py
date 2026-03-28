import os
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import insert
from datetime import datetime
from app.db.models import Embedding as EmbeddingModel
from app.db.database import database
import uuid
import logging
import asyncio

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(ch)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=api_key) 


EMBEDDING_MODEL = "models/gemini-embedding-001" 

def create_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for the given text using the Gemini API.
    """
   
    response = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    
    return response['embedding']

async def create_and_save_embeddings(paper_id: uuid.UUID, chunks: List[str], rate_limit_delay: float = 0.65):
    """
    Generates embeddings for a list of text chunks and saves them to the database.
    Includes rate limiting to avoid exceeding API quota (100 requests/min = ~0.65s per request).
    """
    logger.info(f"Starting embedding creation for paper {paper_id} with {len(chunks)} chunks (rate limited)")
    embedding_data = []
    
    for i, chunk in enumerate(chunks):
        try:
            vector = create_embedding(chunk)
            embedding_data.append({
                "id": uuid.uuid4(),
                "chunk_id": i,
                "vector": vector,
                "created_at": datetime.utcnow(),
                "paper_id": paper_id,
            })
            logger.debug(f"Created embedding for chunk {i}")
            # Rate limiting: sleep to avoid hitting quota (100/min = 0.65s per request)
            await asyncio.sleep(rate_limit_delay)
        except Exception as e:
            # Handle potential API errors gracefully
            logger.error(f"Error creating embedding for chunk {i}: {e}", exc_info=True)
            await asyncio.sleep(rate_limit_delay)
            continue # Skip this chunk and move to the next

    logger.info(f"Created embeddings for {len(embedding_data)} out of {len(chunks)} chunks")
    
    if embedding_data:
        try:
            result = await database.execute(insert(EmbeddingModel).values(embedding_data))
            logger.info(f"Successfully saved {len(embedding_data)} embeddings to database for paper {paper_id}")
        except Exception as e:
            logger.error(f"Error inserting embeddings into the database: {e}", exc_info=True)
    else:
        logger.warning(f"No embeddings were created for paper {paper_id}")