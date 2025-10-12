from databases import Database
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import os

DATABASE_URL = os.getenv("DOCKER_DATABASE_URL", settings.DATABASE_URL)

database = Database(DATABASE_URL)
Base = declarative_base()