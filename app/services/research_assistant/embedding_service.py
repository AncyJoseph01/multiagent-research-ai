import os
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv


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