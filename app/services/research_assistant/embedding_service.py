import os
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import insert
from datetime import datetime
from app.db.models import Embedding as EmbeddingModel
from app.db.database import database
import uuid

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=api_key) 


EMBEDDING_MODEL = "models/embedding-001" 

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

async def create_and_save_embeddings(paper_id: uuid.UUID, chunks: List[str]):
    """
    Generates embeddings for a list of text chunks and saves them to the database.
    """
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
        except Exception as e:
            # Handle potential API errors gracefully
            print(f"Error creating embedding for chunk {i}: {e}")
            continue # Skip this chunk and move to the next

    if embedding_data:
        try:
            await database.execute(insert(EmbeddingModel).values(embedding_data))
        except Exception as e:
            print(f"Error inserting embeddings into the database: {e}")