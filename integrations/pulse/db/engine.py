"""SQLAlchemy async engine and session factory.

Usage:
    from integrations.pulse.db.engine import get_session

    async with get_session() as session:
        result = await session.execute(select(CheckIn))
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pulse:pulse@localhost:5432/aios_pulse",
)

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, rolling back on error."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
