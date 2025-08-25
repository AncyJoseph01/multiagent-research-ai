from PyPDF2 import PdfReader
import io

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
    Splits a long text into smaller chunks with optional overlap.
    """
    if not text:
        return []

    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        chunks.append(text[start_index:end_index])
        start_index += chunk_size - chunk_overlap
        
    return chunks