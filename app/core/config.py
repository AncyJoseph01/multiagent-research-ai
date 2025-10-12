from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    DOCKER_DATABASE_URL: str | None = None

    class Config:
        env_file = ".env",
        extra = "ignore"

settings = Settings()