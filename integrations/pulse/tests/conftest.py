"""Shared test configuration.

Sets up:
- An in-memory SQLite database isolated per-test (no file on disk).
- Override factories for get_current_user and get_current_user_with_role.
- A pytest fixture that provides test-scoped DB sessions.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure executive session keywords are set for tests
os.environ.setdefault(
    "EXECUTIVE_SESSION_KEYWORDS",
    "executive session,exec session,board executive",
)

# Use in-memory SQLite for tests — completely isolated, no file state
TEST_DATABASE_URL = "sqlite:///:memory:"

from integrations.pulse.core.database import Base, get_db, _seed_compliance_items

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(_test_engine, "connect")
def _set_pragmas(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestSessionLocal = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)


def _create_test_schema():
    """Create tables in the in-memory DB (idempotent)."""
    import integrations.pulse.core.models  # noqa: F401 -- register all models
    Base.metadata.create_all(bind=_test_engine)


_create_test_schema()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """Provide a test-scoped database session, rolled back after each test."""
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)

    # Seed compliance items for this test if table is empty
    _seed_compliance_items(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def admin_client(db_session):
    """TestClient authenticated as ADMIN (President / Dave)."""
    from integrations.pulse.app import app
    from integrations.pulse.core.auth import get_current_user, get_current_user_with_role
    from integrations.pulse.core.store import checkin_store

    mock_user = {
        "user_id": "dave@chca.org",
        "preferred_username": "dave@chca.org",
        "role": "ADMIN",
        "role_detail": "president",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_role] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: db_session
    checkin_store._checkins.clear()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def sectreasurer_client(db_session):
    """TestClient authenticated as OFFICER SecTreas."""
    from integrations.pulse.app import app
    from integrations.pulse.core.auth import get_current_user, get_current_user_with_role

    mock_user = {
        "user_id": "sectreasurer@chca.org",
        "preferred_username": "sectreasurer@chca.org",
        "role": "OFFICER",
        "role_detail": "sectreasurer",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_role] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def execsec_client(db_session):
    """TestClient authenticated as OFFICER ExecSec."""
    from integrations.pulse.app import app
    from integrations.pulse.core.auth import get_current_user, get_current_user_with_role

    mock_user = {
        "user_id": "execsec@chca.org",
        "preferred_username": "execsec@chca.org",
        "role": "OFFICER",
        "role_detail": "execsecretary",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_role] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def staff_client(db_session):
    """TestClient authenticated as standard STAFF."""
    from integrations.pulse.app import app
    from integrations.pulse.core.auth import get_current_user, get_current_user_with_role
    from integrations.pulse.core.store import checkin_store

    mock_user = {
        "user_id": "staff4@chca.org",
        "preferred_username": "staff4@chca.org",
        "role": "STAFF",
        "role_detail": "staff",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_role] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: db_session
    checkin_store._checkins.clear()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
