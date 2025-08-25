# import uuid
# import logging
# from fastapi import HTTPException
# from sqlalchemy import insert
# from datetime import date, datetime
# from typing import Optional

# from app.db.database import database
# from app.db.models import Paper, Summary
# from app.services.research_assistant import embedding_service
# from app.services.research_assistant import pdf_service
# from app.services.research_assistant import summariser_service
# from app.schema.paper import Paper as PaperSchema
# from app.schema.summary import SummaryCreate

# logger = logging.getLogger(__name__)

# async def process_and_save_paper(
#     title: str,
#     abstract: str,
#     authors: str,
#     arxiv_id: Optional[str],
#     url: Optional[str],
#     published_at: Optional[date],
#     content: str,
#     user_id: uuid.UUID
# ) -> PaperSchema:
#     """Helper function to process and save a paper, its summary, and embeddings."""
#     paper_id = uuid.uuid4()
#     now = datetime.utcnow()
#     try:
#         logger.info(f"Starting to process paper: {title}")

#         # Save paper metadata
#         paper_data = {
#             "id": paper_id,
#             "title": title,
#             "abstract": abstract,
#             "authors": authors,
#             "arxiv_id": arxiv_id,
#             "url": url,
#             "published_at": published_at,
#             "created_at": now,
#             "user_id": user_id,
#         }
#         await database.execute(insert(Paper).values(**paper_data))
#         logger.info(f"Saved paper metadata with ID: {paper_id}")

#         # Summarise and save content
#         logger.info("Calling summarisation service...")
#         summary_content = summariser_service.summarise_text(content)
        
#         summary_data = {
#             "id": uuid.uuid4(),  
#             "paper_id": paper_id,
#             "summary_type": "structured",
#             "content": summary_content,
#             "created_at": now, 
#         }
#         await database.execute(insert(Summary).values(summary_data))
#         logger.info("Saved structured summary.")

#         # Correct code for chunking and embedding
#         logger.info("Splitting content into chunks for embedding.")
#         chunks = pdf_service.split_text_into_chunks(content)

#         logger.info(f"Creating and saving embeddings for {len(chunks)} chunks.")
#         await embedding_service.create_and_save_embeddings(paper_id, chunks)

#         logger.info("Finished processing.")
        
#         return PaperSchema(**paper_data)
#     except Exception as e:
#         logger.error(f"Failed to process paper: {title}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to process paper: {str(e)}")