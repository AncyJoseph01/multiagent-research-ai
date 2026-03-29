from PyPDF2 import PdfReader
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter

def extract_pdf_text(file_content: bytes) -> str:
    """
    Extract raw text from PDF file content.
    """
    reader = PdfReader(io.BytesIO(file_content))
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def split_text_into_chunks(text: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits a long text into smaller, semantically meaningful chunks with overlap.
    Uses RecursiveCharacterTextSplitter to respect paragraphs and sentences.
    """
    if not text:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],  # Split by paragraph, then line, then sentence
    )
    
    chunks = text_splitter.split_text(text)
    return chunks