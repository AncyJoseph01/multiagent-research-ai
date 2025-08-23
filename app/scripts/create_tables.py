import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base
from app.core.config import settings

async def create_tables():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("[✅] All tables created successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())