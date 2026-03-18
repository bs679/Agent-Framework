"""SQLAlchemy engine and session factory for Pulse.

Dev: SQLite at data/pulse.db (relative to project root).
Prod: Set DATABASE_URL env var to a PostgreSQL DSN.

All models import ``Base`` from here so Alembic can discover them via
``target_metadata`` in the env.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from integrations.pulse.db.base import Base  # noqa: F401  imported for side-effects

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "pulse.db"
)


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", os.environ.get("PULSE_DB_URL", ""))
    if url:
        return url
    _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_DB_PATH}"


def _make_engine():
    url = _get_database_url()
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    kwargs["echo"] = os.environ.get("PULSE_DB_ECHO", "").lower() in ("true", "1")
    return create_engine(url, **kwargs)


engine = _make_engine()

# Expose DATABASE_URL for Alembic env.py
DATABASE_URL: str = _get_database_url()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and ensures it closes after use
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a DB session; close on exit. Use as FastAPI Depends."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table creation helper (used by tests and Alembic env.py)
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """Create all tables if they don't exist. Alembic handles prod migrations."""
    # Import models so their metadata is registered with Base
    import integrations.pulse.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
