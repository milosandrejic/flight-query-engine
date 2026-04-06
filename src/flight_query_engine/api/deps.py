from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.flight_query_engine.database.session import get_session

# yield (not return) so FastAPI runs cleanup after the request finishes,
# ensuring the session is always closed — even if the request errors out.
async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session

# Type alias so routes can use `session: DbSession` instead of
# `session: AsyncSession = Depends(get_db)`
DbSession = Annotated[AsyncSession, Depends(get_db)]
