from __future__ import annotations

from asyncio import current_task
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.sql import text

from realtime_messaging.config import settings


class SessionManager:
    """Manages asynchronous DB sessions with connection pooling."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def init_db(self) -> None:
        """Initialize the database engine and session factory."""
        # Parse the database URL to convert it to async format
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql+asyncpg://"):
            # If it's not already async, make it async
            database_url = database_url.replace("postgresql", "postgresql+asyncpg", 1)

        self.engine = create_async_engine(
            database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1 hour
            echo=settings.debug,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )

    async def close(self) -> None:
        """Dispose of the database engine."""
        if self.engine:
            await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a database session."""
        if not self.session_factory:
            raise RuntimeError("Database session factory is not initialized.")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise RuntimeError(f"Database session error: {e!r}") from e


# Global session manager instance
sessionmanager = SessionManager()


# Dependency function for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async for session in sessionmanager.get_session():
        yield session


