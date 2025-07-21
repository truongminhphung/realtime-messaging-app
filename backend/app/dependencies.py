from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.depends import get_db


# Re-export the database dependency for convenience
async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db():
        yield session


# Database dependency for FastAPI routes
DatabaseDep = Depends(get_database)