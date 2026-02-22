"""Alembic migration environment.

Supports both offline (--sql) and online (async engine) migration modes.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Import models so Alembic can detect schema changes
from integrations.pulse.db.models import Base  # noqa: F401

# Alembic Config object
config = context.config

# Logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read DATABASE_URL from environment (overrides alembic.ini sqlalchemy.url)
_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pulse:pulse@localhost:5432/aios_pulse",
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script)."""
    context.configure(
        url=_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    engine = create_async_engine(_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
