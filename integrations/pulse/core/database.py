"""SQLAlchemy database engine and session management for Pulse.

Uses SQLite for development (configurable via DATABASE_URL env var).
In production, swap DATABASE_URL to a PostgreSQL+asyncpg or psycopg2 DSN.

Session lifecycle
-----------------
Use ``get_db()`` as a FastAPI dependency in route functions.  The session
is committed and closed automatically at the end of each request.

    @router.get("/example")
    def read_example(db: Session = Depends(get_db)):
        ...
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./pulse_dev.db",
)

# SQLite needs check_same_thread=False so FastAPI's thread pool can reuse
# connections safely.  This flag is ignored for non-SQLite engines.
_connect_args: dict = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    # Echo SQL in dev; set SQLALCHEMY_ECHO=false to silence
    echo=os.environ.get("SQLALCHEMY_ECHO", "false").lower() in ("true", "1"),
)

# Enable WAL mode for SQLite to allow concurrent reads during writes
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Base class for ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Declarative base shared by all Pulse ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session; always close it when done."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and run seed data if needed.

    Safe to call on every startup — SQLAlchemy's ``create_all`` is
    idempotent (it only creates tables that don't already exist).
    """
    # Import models so their metadata is registered on Base before create_all
    from integrations.pulse.core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Run seed data for compliance items
    with SessionLocal() as db:
        _seed_compliance_items(db)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_compliance_items(db: Session) -> None:
    """Insert the 8 baseline compliance obligations if not already present."""
    from integrations.pulse.core.models import ComplianceItem

    # Only seed when the table is empty
    if db.query(ComplianceItem).count() > 0:
        return

    from datetime import date, timedelta

    today = date.today()

    items = [
        ComplianceItem(
            title="Monthly dues remittance reconciliation",
            description=(
                "Reconcile dues collected with amounts remitted to the "
                "international union.  Compare payroll deduction reports "
                "against AFSCME remittance records."
            ),
            category="financial",
            frequency="monthly",
            next_due=(today.replace(day=1) + timedelta(days=32)).replace(day=1),
            assigned_to_role="OFFICER",
            status="upcoming",
            notes="Owned by Secretary-Treasurer.",
        ),
        ComplianceItem(
            title="Quarterly executive board meeting",
            description=(
                "Quarterly meeting of the executive board as required by "
                "CHCA bylaws.  Dave chairs; minutes drafted by ExecSec."
            ),
            category="bylaw",
            frequency="quarterly",
            next_due=_next_quarter_date(today),
            assigned_to_role="ALL",
            status="upcoming",
            notes="All officers and executive board members must attend.",
        ),
        ComplianceItem(
            title="Annual LM-2 financial disclosure filing",
            description=(
                "File the LM-2 Labor Organization Annual Report with the "
                "U.S. Department of Labor (OLMS) within 90 days of the "
                "fiscal year end."
            ),
            category="reporting",
            frequency="annual",
            next_due=today.replace(month=3, day=31)
            if today.month <= 3
            else today.replace(year=today.year + 1, month=3, day=31),
            assigned_to_role="OFFICER",
            status="upcoming",
            notes="Secretary-Treasurer responsible.  90-day deadline after FY close.",
        ),
        ComplianceItem(
            title="Annual election of officers",
            description=(
                "Conduct officer elections per Article V of the CHCA bylaws. "
                "Nominations must open at least 30 days before the election meeting."
            ),
            category="bylaw",
            frequency="annual",
            next_due=today.replace(month=11, day=1)
            if today.month < 11
            else today.replace(year=today.year + 1, month=11, day=1),
            assigned_to_role="ALL",
            status="upcoming",
            notes="Bylaw requirement.  Coordinate with nominations committee.",
        ),
        ComplianceItem(
            title="Annual budget approval",
            description=(
                "Present and vote on the annual operating budget at the "
                "executive board meeting.  SecTreas prepares the draft."
            ),
            category="financial",
            frequency="annual",
            next_due=today.replace(month=1, day=31)
            if today.month == 1
            else today.replace(year=today.year + 1, month=1, day=31),
            assigned_to_role="ALL",
            status="upcoming",
            notes="Executive board vote required.",
        ),
        ComplianceItem(
            title="Annual audit",
            description=(
                "Independent review of CHCA financial records.  "
                "SecTreas coordinates with auditor and provides all "
                "supporting documentation."
            ),
            category="financial",
            frequency="annual",
            next_due=today.replace(month=6, day=30)
            if today.month <= 6
            else today.replace(year=today.year + 1, month=6, day=30),
            assigned_to_role="OFFICER",
            status="upcoming",
            notes="Secretary-Treasurer responsible.",
        ),
        ComplianceItem(
            title="Monthly grievance log review",
            description=(
                "President reviews all open grievances for deadline risks, "
                "pattern analysis, and escalation decisions."
            ),
            category="legal",
            frequency="monthly",
            next_due=(today.replace(day=1) + timedelta(days=32)).replace(day=1),
            assigned_to_role="ADMIN",
            status="upcoming",
            notes="President-only review.  Feeds into monthly agent briefing.",
        ),
        ComplianceItem(
            title="Semi-annual member meetings",
            description=(
                "General membership meetings held twice per year per CHCA "
                "bylaws.  President presides; minutes required."
            ),
            category="bylaw",
            frequency="annual",  # stored as annual; frequency note in description
            next_due=_next_semiannual_date(today),
            assigned_to_role="ALL",
            status="upcoming",
            notes="Two per year (spring + fall).  Adequate notice required by bylaws.",
        ),
    ]

    db.add_all(items)
    db.commit()


def _next_quarter_date(today) -> "date":
    """Return the first day of the next calendar quarter."""
    from datetime import date

    quarter_starts = [1, 4, 7, 10]
    for month in quarter_starts:
        if today.month < month:
            return date(today.year, month, 1)
    return date(today.year + 1, 1, 1)


def _next_semiannual_date(today) -> "date":
    """Return next semi-annual meeting date (May 1 or October 1)."""
    from datetime import date

    if today.month < 5:
        return date(today.year, 5, 1)
    if today.month < 10:
        return date(today.year, 10, 1)
    return date(today.year + 1, 5, 1)
