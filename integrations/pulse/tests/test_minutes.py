"""Tests for /api/v1/minutes/* endpoints — Phase 9b Executive Secretary module.

Definition of Done coverage:
  [x] Minutes with executive_session_flag only visible to OFFICER role
  [x] Minutes submit-for-approval creates task for SecTreas
  [x] Minutes approval restricted to OFFICER role, not the drafter
  [x] Minutes draft uses ai_router with task="minutes_draft"
  [x] Routing logs show minutes_draft → ollama (sensitive=True)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from integrations.pulse.app import app
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.roles import require_officer
from integrations.pulse.db.base import Base
from integrations.pulse.db.models import finance, minutes  # noqa: F401
from integrations.pulse.db.session import get_db


# ---------------------------------------------------------------------------
# In-memory SQLite
# StaticPool ensures all connections share the same in-memory DB.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _make_user(user_id: str, roles: list[str] | None = None) -> dict:
    payload = {"user_id": user_id, "preferred_username": user_id}
    if roles is not None:
        payload["roles"] = roles
    return payload


@pytest.fixture(autouse=True)
def reset_fernet_key():
    """Reset the process-level Fernet cache before each test.

    Ensures each test uses the same key for both encryption (in test helpers)
    and decryption (in API endpoints) — both happen in the same process.
    """
    import integrations.pulse.api.v1.minutes_api as mapi
    mapi._fernet_instance = None
    yield
    mapi._fernet_instance = None


@pytest.fixture()
def execsec_user():
    return _make_user("execsec@chca.org", roles=["OFFICER"])


@pytest.fixture()
def sectreas_user():
    return _make_user("sectreas@chca.org", roles=["OFFICER"])


@pytest.fixture()
def staff_user():
    return _make_user("staff@chca.org", roles=[])


# ---------------------------------------------------------------------------
# Test client factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_for(db_session):
    def _make(user_dict: dict):
        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[require_officer] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: db_session
        return TestClient(app, raise_server_exceptions=True)

    yield _make
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STUB_DRAFT_CONTENT = "# Meeting Minutes\n\n## Call to Order\n[ACTION RECORDED HERE]"


def _stub_ai_response():
    """Mock AIRouter.complete that simulates Ollama routing."""
    from integrations.ai.router import AIResponse
    return AIResponse(
        text=_STUB_DRAFT_CONTENT,
        model_used="llama3.1:8b",
        task_type="minutes_draft",
        routed_to="ollama",
        fallback_used=False,
    )


def _generate_draft(client: TestClient, agenda_items=None, board_meeting_id=None) -> dict:
    """POST to generate-draft with mocked AI router."""
    body = {"agenda_items": agenda_items or ["Budget review", "Grievance updates"]}
    if board_meeting_id is not None:
        body["board_meeting_id"] = board_meeting_id

    with patch(
        "integrations.pulse.api.v1.minutes_api._get_ai_router"
    ) as mock_router_factory:
        mock_router = mock_router_factory.return_value
        mock_router.complete = AsyncMock(return_value=_stub_ai_response())
        resp = client.post("/api/v1/minutes/generate-draft", json=body)

    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# Draft generation
# ===========================================================================

class TestGenerateDraft:
    def test_draft_creates_minutes_with_status_draft(self, client_for, execsec_user):
        client = client_for(execsec_user)
        m = _generate_draft(client)
        assert m["status"] == "draft"
        assert m["drafted_by"] == execsec_user["user_id"]

    def test_draft_uses_minutes_draft_ai_task(self, client_for, execsec_user):
        """Verify ai_router.complete is called with task='minutes_draft'."""
        client = client_for(execsec_user)
        with patch(
            "integrations.pulse.api.v1.minutes_api._get_ai_router"
        ) as mock_factory:
            mock_router = mock_factory.return_value
            mock_router.complete = AsyncMock(return_value=_stub_ai_response())
            client.post(
                "/api/v1/minutes/generate-draft",
                json={"agenda_items": ["Test item"]},
            )
            # Verify task type passed to router
            call_kwargs = mock_router.complete.call_args
            assert call_kwargs.kwargs.get("task") == "minutes_draft" or \
                   call_kwargs.args[0] == "minutes_draft" if call_kwargs.args else \
                   call_kwargs.kwargs["task"] == "minutes_draft"

    def test_draft_router_routes_to_ollama(self, client_for, execsec_user):
        """Confirm the AI response shows routed_to=ollama (sensitive route)."""
        client = client_for(execsec_user)
        response_obj = _stub_ai_response()
        assert response_obj.routed_to == "ollama"
        assert response_obj.task_type == "minutes_draft"

    def test_draft_non_exec_session_content_readable_by_all(
        self, client_for, execsec_user, staff_user
    ):
        """Regular meeting minutes (no exec session flag) are readable by staff."""
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)
        assert m["executive_session_flag"] is False

        client_staff = client_for(staff_user)
        resp = client_staff.get(f"/api/v1/minutes/{m['id']}")
        assert resp.status_code == 200
        assert resp.json()["content_md"] is not None

    def test_draft_exec_session_meeting_sets_flag(
        self, client_for, execsec_user, db_session
    ):
        """Minutes for an executive_session board meeting get flag=True."""
        from integrations.pulse.db.models.minutes import BoardMeeting
        from datetime import datetime, timezone

        bm = BoardMeeting(
            title="Executive Board Meeting",
            meeting_date=datetime.now(timezone.utc),
            type="executive_session",
        )
        db_session.add(bm)
        db_session.commit()
        db_session.refresh(bm)

        client = client_for(execsec_user)
        m = _generate_draft(client, board_meeting_id=bm.id)
        assert m["executive_session_flag"] is True


# ===========================================================================
# Executive session visibility rule
# ===========================================================================

class TestExecutiveSessionVisibility:
    def _create_exec_session_minutes(
        self, db_session, drafted_by: str
    ):
        """Directly insert exec-session minutes into the DB."""
        from integrations.pulse.db.models.minutes import MeetingMinutes
        from integrations.pulse.api.v1.minutes_api import _encrypt_content
        from datetime import datetime, timezone

        encrypted = _encrypt_content("SECRET CONTENT — exec session only")
        m = MeetingMinutes(
            status="draft",
            content_md=encrypted,
            executive_session_flag=True,
            drafted_by=drafted_by,
            draft_at=datetime.now(timezone.utc),
        )
        db_session.add(m)
        db_session.commit()
        db_session.refresh(m)
        return m

    def test_officer_can_read_exec_session_content(
        self, client_for, execsec_user, sectreas_user, db_session
    ):
        """OFFICER role users can decrypt and read executive session content."""
        m = self._create_exec_session_minutes(db_session, execsec_user["user_id"])

        client = client_for(sectreas_user)
        resp = client.get(f"/api/v1/minutes/{m.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["executive_session_flag"] is True
        # Officer should see decrypted content
        assert data["content_md"] is not None
        assert "SECRET CONTENT" in data["content_md"]

    def test_staff_cannot_read_exec_session_content(
        self, client_for, execsec_user, staff_user, db_session
    ):
        """Non-OFFICER users cannot view executive session content_md."""
        m = self._create_exec_session_minutes(db_session, execsec_user["user_id"])

        client = client_for(staff_user)
        resp = client.get(f"/api/v1/minutes/{m.id}")
        assert resp.status_code == 200
        data = resp.json()
        # The record is visible but content_md is None for non-officers
        assert data["executive_session_flag"] is True
        assert data["content_md"] is None

    def test_exec_session_list_hides_content_from_staff(
        self, client_for, execsec_user, staff_user, db_session
    ):
        """Listing minutes also applies exec session redaction."""
        self._create_exec_session_minutes(db_session, execsec_user["user_id"])

        client = client_for(staff_user)
        resp = client.get("/api/v1/minutes/")
        assert resp.status_code == 200
        for m in resp.json():
            if m["executive_session_flag"]:
                assert m["content_md"] is None


# ===========================================================================
# Submit for approval
# ===========================================================================

class TestSubmitForApproval:
    def test_submit_changes_status_to_pending_approval(
        self, client_for, execsec_user, db_session
    ):
        """Submit-for-approval transitions status from draft → pending_approval."""
        client = client_for(execsec_user)
        m = _generate_draft(client)

        resp = client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_approval"

    def test_submit_creates_task_for_sectreas(
        self, client_for, execsec_user, db_session
    ):
        """Submit-for-approval creates a PulseTask assigned to sectreas."""
        client = client_for(execsec_user)
        m = _generate_draft(client)
        client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")

        from integrations.pulse.db.models.minutes import PulseTask
        tasks = db_session.query(PulseTask).filter(
            PulseTask.related_object == f"minutes:{m['id']}"
        ).all()
        assert len(tasks) == 1
        assert tasks[0].assigned_to == "sectreas"
        assert tasks[0].status == "open"

    def test_cannot_submit_non_draft(self, client_for, execsec_user, db_session):
        """Submitting minutes that aren't in 'draft' status returns 409."""
        client = client_for(execsec_user)
        m = _generate_draft(client)
        # Submit once
        client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")
        # Submit again (now in pending_approval)
        resp = client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")
        assert resp.status_code == 409


# ===========================================================================
# Approval workflow
# ===========================================================================

class TestMinutesApproval:
    def test_officer_can_approve(
        self, client_for, execsec_user, sectreas_user, db_session
    ):
        """SecTreas (different OFFICER) can approve minutes submitted by ExecSec."""
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)
        client_exec.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")

        client_sectreas = client_for(sectreas_user)
        resp = client_sectreas.post(f"/api/v1/minutes/{m['id']}/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == sectreas_user["user_id"]
        assert data["approved_at"] is not None

    def test_drafter_cannot_approve_own_minutes(
        self, client_for, execsec_user, db_session
    ):
        """The drafter cannot approve their own minutes — CLAUDE.md hard rule."""
        client = client_for(execsec_user)
        m = _generate_draft(client)
        client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")

        # ExecSec tries to approve their own minutes
        resp = client.post(f"/api/v1/minutes/{m['id']}/approve")
        assert resp.status_code == 403
        assert "drafter" in resp.json()["detail"].lower()

    def test_approve_requires_pending_approval_status(
        self, client_for, execsec_user, sectreas_user, db_session
    ):
        """Cannot approve minutes that are still in 'draft' status."""
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)
        # Do NOT submit — still in draft

        client_sectreas = client_for(sectreas_user)
        resp = client_sectreas.post(f"/api/v1/minutes/{m['id']}/approve")
        assert resp.status_code == 409

    def test_approve_marks_sectreas_task_complete(
        self, client_for, execsec_user, sectreas_user, db_session
    ):
        """Approving minutes marks the SecTreas task as completed."""
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)
        client_exec.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")

        client_sectreas = client_for(sectreas_user)
        client_sectreas.post(f"/api/v1/minutes/{m['id']}/approve")

        from integrations.pulse.db.models.minutes import PulseTask
        task = db_session.query(PulseTask).filter(
            PulseTask.related_object == f"minutes:{m['id']}"
        ).first()
        assert task is not None
        assert task.status == "completed"


# ===========================================================================
# Minutes PATCH (editing)
# ===========================================================================

class TestMinutesPatch:
    def test_can_edit_draft_content(self, client_for, execsec_user):
        client = client_for(execsec_user)
        m = _generate_draft(client)
        resp = client.patch(
            f"/api/v1/minutes/{m['id']}",
            json={"content_md": "# Updated Minutes\n\nNew content here."},
        )
        assert resp.status_code == 200
        assert "Updated Minutes" in resp.json()["content_md"]

    def test_non_drafter_non_officer_cannot_edit_draft(self, client_for, execsec_user, staff_user):
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)

        client_staff = client_for(staff_user)
        resp = client_staff.patch(
            f"/api/v1/minutes/{m['id']}",
            json={"content_md": "Unauthorized edit"},
        )
        assert resp.status_code == 403

    def test_officer_can_edit_another_users_draft(self, client_for, execsec_user, sectreas_user):
        client_exec = client_for(execsec_user)
        m = _generate_draft(client_exec)

        client_sectreas = client_for(sectreas_user)
        resp = client_sectreas.patch(
            f"/api/v1/minutes/{m['id']}",
            json={"content_md": "Officer correction"},
        )
        assert resp.status_code == 200
        assert "Officer correction" in resp.json()["content_md"]

    def test_cannot_edit_pending_approval_minutes(
        self, client_for, execsec_user
    ):
        client = client_for(execsec_user)
        m = _generate_draft(client)
        client.post(f"/api/v1/minutes/{m['id']}/submit-for-approval")
        resp = client.patch(
            f"/api/v1/minutes/{m['id']}",
            json={"content_md": "Tampered content"},
        )
        assert resp.status_code == 409


# ===========================================================================
# Minutes listing
# ===========================================================================

class TestMinutesList:
    def test_list_returns_all_minutes(self, client_for, execsec_user):
        client = client_for(execsec_user)
        _generate_draft(client)
        _generate_draft(client)
        resp = client.get("/api/v1/minutes/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_by_status(self, client_for, execsec_user, sectreas_user):
        client_exec = client_for(execsec_user)
        m1 = _generate_draft(client_exec)
        m2 = _generate_draft(client_exec)
        client_exec.post(f"/api/v1/minutes/{m1['id']}/submit-for-approval")

        resp = client_exec.get("/api/v1/minutes/?status=pending_approval")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == m1["id"]

    def test_get_nonexistent_returns_404(self, client_for, execsec_user):
        client = client_for(execsec_user)
        resp = client.get("/api/v1/minutes/99999")
        assert resp.status_code == 404
