# import logging
# from fastapi import APIRouter, UploadFile, File, HTTPException
# import uuid
# from typing import List

# from app.services.research_assistant import pdf_service
# from app.services.research_assistant import process_and_save_paper
# from app.schema.paper import Paper as PaperSchema
# # from app.core.config import MOCK_USER_ID

# logger = logging.getLogger(__name__)

# router = APIRouter()
# MOCK_USER_ID = uuid.UUID("bc3283ba-3093-423d-94a4-6482fddd27ff")
# @router.post("/papers/upload", response_model=PaperSchema)
# async def upload_pdf_paper(file: UploadFile = File(...)):
#     """
#     Accepts a PDF file from a user, extracts its content,
#     and saves the paper, summary, and embeddings to the database.
#     """
#     logger.info(f"Received request to upload PDF file: {file.filename}")

#     try:
#         # Step 1: Read the PDF file content
#         pdf_content = await file.read()
        
#         # Step 2: Extract text from the PDF
#         extracted_text = pdf_service.extract_pdf_text(pdf_content)
#         if not extracted_text:
#             raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
        
#         # Use a placeholder title and abstract for now.
#         title = file.filename.replace(".pdf", "").replace("_", " ").title()
#         abstract = extracted_text[:200] + "..."
        
#         # Step 3: Process and save the paper using the full text
#         processed_paper = await process_and_save_paper(
#             title=title,
#             abstract=abstract,
#             authors="User Upload",
#             arxiv_id=None,
#             url=None,
#             published_at=None,
#             content=extracted_text,
#             user_id=MOCK_USER_ID
#         )
        
#         logger.info(f"Successfully processed and saved uploaded paper: {title}")
#         return processed_paper
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error processing uploaded PDF: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
