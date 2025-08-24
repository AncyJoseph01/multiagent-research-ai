import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def summarise_text(content: str) -> str:
    """
    Summarise text into structured research notes.
    """
    prompt = f"""
    Summarise the following text into structured research notes with:
    - Abstract
    - Methods
    - Findings

    Text:
    {content}
    """
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    return response.text
