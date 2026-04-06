from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.flight_query_engine.config import settings

engine = create_async_engine(settings.database_url, echo=settings.is_development)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
