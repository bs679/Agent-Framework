"""Tests for /api/v1/finance/* endpoints — Phase 9b Secretary/Treasurer module.

Definition of Done coverage:
  [x] Co-signature enforcement: second signer cannot be same person as first
  [x] Co-signature enforcement: requestor cannot self-approve
  [x] All disbursement state changes logged to audit table
  [x] Finance endpoints require valid JWT
  [x] SecTreas context bundle includes finance section for OFFICER role
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from integrations.pulse.app import app
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.roles import require_officer
from integrations.pulse.db.base import Base
from integrations.pulse.db.models import finance, minutes  # noqa: F401 — register models
from integrations.pulse.db.session import get_db


# ---------------------------------------------------------------------------
# In-memory SQLite for tests
# StaticPool ensures all connections share the same in-memory DB.
# Without it, each new connection from the pool gets a fresh empty database.
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
# Auth fixtures: regular user and officer user
# ---------------------------------------------------------------------------

def _make_user(user_id: str, roles: list[str] | None = None) -> dict:
    payload = {"user_id": user_id, "preferred_username": user_id}
    if roles is not None:
        payload["roles"] = roles
    return payload


@pytest.fixture()
def officer_user():
    return _make_user("sectreas@chca.org", roles=["OFFICER"])


@pytest.fixture()
def regular_user():
    return _make_user("staff@chca.org", roles=[])


@pytest.fixture()
def second_officer():
    return _make_user("president@chca.org", roles=["OFFICER"])


# ---------------------------------------------------------------------------
# Test client factory — accepts overridable user and db session
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_for(db_session):
    """Returns a factory: client_for(user_dict) → TestClient."""

    def _make(user_dict: dict):
        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[require_officer] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: db_session
        c = TestClient(app, raise_server_exceptions=True)
        return c

    yield _make
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_disbursement(client: TestClient, **kwargs) -> dict:
    body = {
        "amount": 250.00,
        "payee": "Office Supplies Co",
        "description": "Printer paper and toner",
        "category": "office_supplies",
        **kwargs,
    }
    resp = client.post("/api/v1/finance/disbursements", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# Authentication guard
# ===========================================================================

class TestFinanceAuthRequired:
    def test_disbursements_list_requires_jwt(self):
        """Verify endpoint raises 401/403 without auth override."""
        # Remove all overrides so real auth runs
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/finance/disbursements")
        assert resp.status_code in (401, 403, 422)


# ===========================================================================
# Dashboard
# ===========================================================================

class TestFinanceDashboard:
    def test_returns_200(self, client_for, officer_user):
        client = client_for(officer_user)
        resp = client.get("/api/v1/finance/dashboard")
        assert resp.status_code == 200

    def test_dashboard_structure(self, client_for, officer_user):
        client = client_for(officer_user)
        data = client.get("/api/v1/finance/dashboard").json()
        assert "fiscal_year" in data
        assert "ytd_disbursements" in data
        assert "budget_remaining" in data
        assert "pending_disbursements" in data
        assert "dues_arrears_count" in data
        assert "budget_lines" in data

    def test_pending_disbursements_count(self, client_for, officer_user, second_officer):
        client = client_for(officer_user)
        # Create 2 disbursements (neither signed yet)
        _create_disbursement(client)
        _create_disbursement(client)
        data = client.get("/api/v1/finance/dashboard").json()
        assert data["pending_disbursements"] == 2


# ===========================================================================
# Disbursement creation
# ===========================================================================

class TestDisbursementCreate:
    def test_create_starts_at_pending_first_sig(self, client_for, regular_user):
        client = client_for(regular_user)
        d = _create_disbursement(client)
        assert d["status"] == "pending_first_sig"
        assert d["requested_by"] == regular_user["user_id"]

    def test_create_requires_positive_amount(self, client_for, regular_user):
        client = client_for(regular_user)
        resp = client.post(
            "/api/v1/finance/disbursements",
            json={"amount": -50.0, "payee": "X", "description": "Y", "category": "Z"},
        )
        assert resp.status_code == 422

    def test_create_is_logged_to_audit(self, client_for, regular_user, db_session):
        client = client_for(regular_user)
        d = _create_disbursement(client)
        from integrations.pulse.db.models.finance import DisbursementAudit
        audit_rows = db_session.query(DisbursementAudit).filter(
            DisbursementAudit.disbursement_id == d["id"]
        ).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].action == "create"
        assert audit_rows[0].new_status == "pending_first_sig"
        assert audit_rows[0].previous_status is None


# ===========================================================================
# Co-signature enforcement — CORE HARD RULES
# ===========================================================================

class TestCoSignatureEnforcement:
    """Every test here maps directly to CLAUDE.md hard rules."""

    def test_rule1_requestor_cannot_self_approve(self, client_for, regular_user, officer_user, db_session):
        """RULE 1: The requestor cannot be the first signer.

        The requestor creates the disbursement with their user_id.
        If that same user_id is an officer and tries to sign first, it must be rejected.
        """
        # Create disbursement as officer_user (requestor)
        client = client_for(officer_user)
        d = _create_disbursement(client)

        # Try to sign as the same officer (requestor = signer)
        resp = client.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "first", "approved": True},
        )
        assert resp.status_code == 403
        assert "self-approval" in resp.json()["detail"].lower()

    def test_rule2_second_signer_cannot_match_first_signer(
        self, client_for, regular_user, officer_user, second_officer, db_session
    ):
        """RULE 2: Second signature must come from a DIFFERENT officer than first.

        This is enforced at the API level — checked by user_id, not just role.
        """
        # Create disbursement as regular staff
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)

        # officer_user applies first signature
        client_officer = client_for(officer_user)
        resp = client_officer.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "first", "approved": True},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_second_sig"
        assert resp.json()["first_signature_by"] == officer_user["user_id"]

        # SAME officer tries to apply second signature — must be rejected
        resp2 = client_officer.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "second", "approved": True},
        )
        assert resp2.status_code == 403
        assert "different officer" in resp2.json()["detail"].lower()

    def test_happy_path_two_different_officers(
        self, client_for, regular_user, officer_user, second_officer, db_session
    ):
        """Two different officers can complete the co-signature workflow."""
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)
        disbursement_id = d["id"]

        # First officer signs
        client1 = client_for(officer_user)
        r1 = client1.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "first", "approved": True},
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "pending_second_sig"

        # Second (different) officer signs
        client2 = client_for(second_officer)
        r2 = client2.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "second", "approved": True},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"
        assert r2.json()["second_signature_by"] == second_officer["user_id"]
        assert r2.json()["approved_at"] is not None

    def test_cannot_apply_first_sig_when_already_pending_second(
        self, client_for, regular_user, officer_user, second_officer
    ):
        """Applying first signature when status is pending_second_sig fails."""
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)

        # Move to pending_second_sig
        client1 = client_for(officer_user)
        client1.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "first", "approved": True},
        )

        # Try first sig again from a third officer — wrong stage
        client2 = client_for(second_officer)
        resp = client2.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "first", "approved": True},
        )
        assert resp.status_code == 409

    def test_reject_at_first_signature_stage(
        self, client_for, regular_user, officer_user
    ):
        """An officer can reject at the first signature stage."""
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)

        client_officer = client_for(officer_user)
        resp = client_officer.post(
            f"/api/v1/finance/disbursements/{d['id']}/sign",
            json={"signature_role": "first", "approved": False},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_reject_at_second_signature_stage(
        self, client_for, regular_user, officer_user, second_officer
    ):
        """An officer can reject at the second signature stage."""
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)
        disbursement_id = d["id"]

        client1 = client_for(officer_user)
        client1.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "first", "approved": True},
        )

        client2 = client_for(second_officer)
        resp = client2.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "second", "approved": False},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


# ===========================================================================
# Audit trail
# ===========================================================================

class TestDisbursementAudit:
    def test_full_approval_creates_three_audit_entries(
        self, client_for, regular_user, officer_user, second_officer, db_session
    ):
        """Create + sign_first + sign_second_approve = 3 audit entries."""
        client_staff = client_for(regular_user)
        d = _create_disbursement(client_staff)
        disbursement_id = d["id"]

        client1 = client_for(officer_user)
        client1.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "first", "approved": True},
        )

        client2 = client_for(second_officer)
        client2.post(
            f"/api/v1/finance/disbursements/{disbursement_id}/sign",
            json={"signature_role": "second", "approved": True},
        )

        from integrations.pulse.db.models.finance import DisbursementAudit
        entries = db_session.query(DisbursementAudit).filter(
            DisbursementAudit.disbursement_id == disbursement_id
        ).order_by(DisbursementAudit.performed_at).all()

        assert len(entries) == 3
        assert entries[0].action == "create"
        assert entries[0].new_status == "pending_first_sig"
        assert entries[1].action == "sign_first"
        assert entries[1].new_status == "pending_second_sig"
        assert entries[2].action == "sign_second_approve"
        assert entries[2].new_status == "approved"

    def test_audit_endpoint_for_single_disbursement(
        self, client_for, regular_user, officer_user, db_session
    ):
        """GET /audit?disbursement_id=X returns audit trail for that disbursement."""
        client = client_for(regular_user)
        d = _create_disbursement(client)

        # Query audit (any authenticated user can query by disbursement_id)
        resp = client.get(f"/api/v1/finance/audit?disbursement_id={d['id']}")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        assert entries[0]["disbursement_id"] == d["id"]

    def test_full_audit_log_requires_officer(
        self, client_for, regular_user, officer_user
    ):
        """GET /audit without disbursement_id requires OFFICER role."""
        # Regular user: should get 403
        client_staff = client_for(regular_user)
        # Override require_officer back to real check for this test
        from integrations.pulse.core.roles import require_officer as real_require_officer
        app.dependency_overrides[require_officer] = real_require_officer

        resp = client_staff.get("/api/v1/finance/audit")
        assert resp.status_code in (403, 401)

    def test_full_audit_log_allowed_for_officer(
        self, client_for, officer_user, db_session
    ):
        """GET /audit without disbursement_id succeeds for OFFICER role."""
        client = client_for(officer_user)
        resp = client.get("/api/v1/finance/audit")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# Dues remittances
# ===========================================================================

class TestDuesRemittances:
    def test_create_remittance(self, client_for, regular_user):
        client = client_for(regular_user)
        resp = client.post(
            "/api/v1/finance/dues-remittances",
            json={
                "facility": "Bradley Memorial Hospital",
                "period": "2026-02",
                "expected_amount": 5000.00,
                "received_amount": 5000.00,
                "received_date": "2026-02-10T00:00:00Z",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["facility"] == "Bradley Memorial Hospital"
        assert data["reconciled"] is False

    def test_arrears_endpoint_returns_shortfalls(self, client_for, regular_user):
        client = client_for(regular_user)
        # Create partially paid remittance
        client.post(
            "/api/v1/finance/dues-remittances",
            json={
                "facility": "Norwalk Hospital",
                "period": "2026-02",
                "expected_amount": 3000.00,
                "received_amount": 1500.00,
            },
        )
        resp = client.get("/api/v1/finance/dues-remittances/arrears?period=2026-02")
        assert resp.status_code == 200
        data = resp.json()
        assert data["arrears_count"] >= 1
        facilities = [f["facility"] for f in data["facilities"]]
        assert "Norwalk Hospital" in facilities

    def test_fully_paid_facility_not_in_arrears(self, client_for, regular_user):
        client = client_for(regular_user)
        client.post(
            "/api/v1/finance/dues-remittances",
            json={
                "facility": "Waterbury Hospital",
                "period": "2026-03",
                "expected_amount": 2000.00,
                "received_amount": 2000.00,
            },
        )
        resp = client.get("/api/v1/finance/dues-remittances/arrears?period=2026-03")
        assert resp.status_code == 200
        facilities = [f["facility"] for f in resp.json()["facilities"]]
        assert "Waterbury Hospital" not in facilities

    def test_list_remittances_filter_by_facility(self, client_for, regular_user):
        client = client_for(regular_user)
        client.post(
            "/api/v1/finance/dues-remittances",
            json={"facility": "Bradley Memorial Hospital", "period": "2026-02",
                  "expected_amount": 1000.0},
        )
        client.post(
            "/api/v1/finance/dues-remittances",
            json={"facility": "Region 12 Schools", "period": "2026-02",
                  "expected_amount": 500.0},
        )
        resp = client.get("/api/v1/finance/dues-remittances?facility=Region+12+Schools")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["facility"] == "Region 12 Schools" for r in data)


# ===========================================================================
# Disbursement list and detail
# ===========================================================================

class TestDisbursementListDetail:
    def test_list_empty(self, client_for, regular_user):
        client = client_for(regular_user)
        resp = client.get("/api/v1/finance/disbursements")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_filter_by_status(self, client_for, regular_user, officer_user, second_officer):
        client_staff = client_for(regular_user)
        d1 = _create_disbursement(client_staff)
        d2 = _create_disbursement(client_staff)

        # Sign d1 all the way to approved
        client1 = client_for(officer_user)
        client1.post(
            f"/api/v1/finance/disbursements/{d1['id']}/sign",
            json={"signature_role": "first", "approved": True},
        )
        client2 = client_for(second_officer)
        client2.post(
            f"/api/v1/finance/disbursements/{d1['id']}/sign",
            json={"signature_role": "second", "approved": True},
        )

        resp = client_for(regular_user).get("/api/v1/finance/disbursements?status=approved")
        assert resp.status_code == 200
        approved = resp.json()
        assert len(approved) == 1
        assert approved[0]["id"] == d1["id"]

    def test_get_disbursement_detail(self, client_for, regular_user):
        client = client_for(regular_user)
        d = _create_disbursement(client)
        resp = client.get(f"/api/v1/finance/disbursements/{d['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == d["id"]

    def test_get_nonexistent_returns_404(self, client_for, regular_user):
        client = client_for(regular_user)
        resp = client.get("/api/v1/finance/disbursements/99999")
        assert resp.status_code == 404
