from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Multiagent Research AI",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    print("✅ App started with settings:")


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Multiagent Research AI ",
        "database_url": settings.DATABASE_URL,  
    }
