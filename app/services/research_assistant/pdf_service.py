from PyPDF2 import PdfReader

def extract_pdf_text(file_path: str) -> str:
    """
    Extract raw text from PDF file.
    """
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text
