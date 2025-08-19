from databases import Database
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

database = Database(settings.DATABASE_URL)
Base = declarative_base()