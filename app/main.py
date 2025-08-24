from fastapi import FastAPI
from app.db.database import database
from app.api import users, papers, summaries, tasks, events, history, embeddings, research

app = FastAPI()

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Include routers
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(papers.router, prefix="/papers", tags=["papers"])
app.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
app.include_router(research.router, prefix="/research", tags=["research"])