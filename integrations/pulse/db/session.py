"""SQLAlchemy engine and session factory for Pulse persistence layer.

Dev: SQLite at the path configured by PULSE_DB_URL (default: ./pulse.db)
Prod: PostgreSQL via DATABASE_URL override.

All models import ``Base`` from here so Alembic can discover them via
``target_metadata`` in the env.py.
"""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Database URL — override via environment variable for production
# ---------------------------------------------------------------------------
_DEFAULT_DB_URL = "sqlite:///./pulse.db"
DATABASE_URL: str = os.environ.get("PULSE_DB_URL", _DEFAULT_DB_URL)


# ---------------------------------------------------------------------------
# Engine — check_same_thread=False required for SQLite with FastAPI
# ---------------------------------------------------------------------------
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=os.environ.get("PULSE_DB_ECHO", "").lower() in ("true", "1"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Declarative base — shared by all models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and ensures it closes after use
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
