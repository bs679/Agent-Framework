#!/usr/bin/env python3
"""Phase 9c End-to-End Smoke Test.

Runs programmatically against the FastAPI test client (no live server needed).
Logs pass/fail for each of the 8 smoke test checks.

Usage:
    python integrations/pulse/tests/smoke_test_9c.py
"""

from __future__ import annotations

import sys
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# In-memory test DB (single connection — SQLite :memory: is connection-scoped)
# ---------------------------------------------------------------------------
from integrations.pulse.core.database import Base, _seed_compliance_items
from integrations.pulse.core.auth import get_current_user, get_current_user_with_role
from integrations.pulse.core.database import get_db
from integrations.pulse.app import app

import integrations.pulse.core.models  # noqa: F401 — register ORM models

_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False)

# Create schema on a shared, pinned connection so the in-memory DB persists
_shared_connection = _engine.connect()
_shared_connection.begin()
Base.metadata.create_all(bind=_shared_connection)

_db = _SessionLocal(bind=_shared_connection)
_seed_compliance_items(_db)


# ---------------------------------------------------------------------------
# Context manager: set dependency overrides for one role, then clean up
# ---------------------------------------------------------------------------

@contextmanager
def as_role(role: str, role_detail: str, user_id: str):
    """Temporarily set app.dependency_overrides for the given role."""
    mock_user = {
        "user_id": user_id,
        "preferred_username": user_id,
        "role": role,
        "role_detail": role_detail,
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_role] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: _db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Smoke test runner
# ---------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[int, str, str]] = []


def check(n: int, description: str, fn):
    try:
        fn()
        results.append((n, PASS, description))
        print(f"  [PASS] Check {n}: {description}")
    except Exception as exc:
        results.append((n, FAIL, description))
        print(f"  [FAIL] Check {n}: {description}")
        print(f"         {exc}")


# ---------------------------------------------------------------------------
# 8 Smoke test checks
# ---------------------------------------------------------------------------

print("\n=== Phase 9c Smoke Test ===\n")


# Check 1 — Dave's context has grievances, board, legislative
def check_1():
    with as_role("ADMIN", "president", "dave@chca.org") as c:
        data = c.get("/api/v1/agents/context").json()
        assert data["grievances"] is not None, "grievances section missing for ADMIN"
        assert data["board"] is not None, "board section missing for ADMIN"
        assert data["legislative"] is not None, "legislative section missing for ADMIN"
        assert data["compliance"] is not None, "compliance section missing for ADMIN"
        assert data["finance_summary"] is not None, "finance_summary missing for ADMIN"

check(1, "GET /api/v1/agents/context as Dave — grievances/board/legislative/compliance present", check_1)


# Check 2 — Staff context has NO grievances, finance, board, legislative
def check_2():
    with as_role("STAFF", "staff", "staff4@chca.org") as c:
        data = c.get("/api/v1/agents/context").json()
        assert data["grievances"] is None, "STAFF should NOT have grievances section"
        assert data["finance"] is None, "STAFF should NOT have finance detail"
        assert data["finance_summary"] is None, "STAFF should NOT have finance_summary"
        assert data["board"] is None, "STAFF should NOT have board section"
        assert data["legislative"] is None, "STAFF should NOT have legislative section"
        assert data["compliance"] is not None, "STAFF should have compliance section"
        assert data["calendar"] is not None, "STAFF should have calendar"
        assert data["tasks"] is not None, "STAFF should have tasks"
        assert data["email"] is not None, "STAFF should have email"

check(2, "GET /api/v1/agents/context as staff — NO grievances/finance/board; base+compliance only", check_2)


# Check 3 — SecTreas gets full finance detail, not grievances
def check_3():
    with as_role("OFFICER", "sectreasurer", "sectreasurer@chca.org") as c:
        data = c.get("/api/v1/agents/context").json()
        assert data["finance"] is not None, "SecTreas should have finance (detail)"
        assert "pending_amount_usd" in data["finance"], "finance missing amount detail"
        assert data["minutes_pending"] is not None, "SecTreas should have minutes_pending"
        assert data["grievances"] is None, "SecTreas should NOT have grievances"
        assert data["compliance"] is not None, "SecTreas should have compliance"
        # Verify OFFICER compliance items visible
        resp2 = c.get("/api/v1/compliance/").json()
        officer_items = [i for i in resp2["items"] if i["assigned_to_role"] == "OFFICER"]
        assert len(officer_items) > 0, "SecTreas should see OFFICER compliance items"

check(3, "SecTreas context — finance detail + minutes_pending; grievances absent; OFFICER compliance visible", check_3)


# Check 4 — ExecSec gets scheduling + minutes, no finance
def check_4():
    with as_role("OFFICER", "execsecretary", "execsec@chca.org") as c:
        data = c.get("/api/v1/agents/context").json()
        assert data["scheduling"] is not None, "ExecSec should have scheduling section"
        assert data["minutes"] is not None, "ExecSec should have minutes (drafts)"
        assert data["finance"] is None, "ExecSec should NOT have finance"
        assert data["minutes_pending"] is None, "ExecSec should NOT have minutes_pending"
        assert data["compliance"] is not None, "ExecSec should have compliance"

check(4, "ExecSec context — scheduling/minutes present; finance/minutes_pending absent", check_4)


# Check 5 — Compliance calendar seeded with all 8 items visible across roles
def check_5():
    with as_role("ADMIN", "president", "dave@chca.org") as admin_c:
        admin_titles = {i["title"] for i in admin_c.get("/api/v1/compliance/").json()["items"]}

    with as_role("OFFICER", "sectreasurer", "sectreasurer@chca.org") as off_c:
        officer_titles = {i["title"] for i in off_c.get("/api/v1/compliance/").json()["items"]}

    all_visible = admin_titles | officer_titles

    expected = [
        "Monthly dues remittance reconciliation",
        "Quarterly executive board meeting",
        "Annual LM-2 financial disclosure filing",
        "Annual election of officers",
        "Annual budget approval",
        "Annual audit",
        "Monthly grievance log review",
        "Semi-annual member meetings",
    ]
    missing = [t for t in expected if t not in all_visible]
    assert not missing, f"Missing compliance items: {missing}"

check(5, "Compliance calendar — all 8 seeded items visible across ADMIN+OFFICER roles", check_5)


# Check 6 — Staff role filter: staff sees only ALL-assigned compliance items
def check_6():
    with as_role("STAFF", "staff", "staff4@chca.org") as c:
        items = c.get("/api/v1/compliance/").json()["items"]
        for item in items:
            assert item["assigned_to_role"] in ("STAFF", "ALL"), (
                f"Staff sees forbidden item ({item['assigned_to_role']}): {item['title']}"
            )
        titles = [i["title"] for i in items]
        assert "Annual LM-2 financial disclosure filing" not in titles, \
            "LM-2 (OFFICER) should NOT be visible to STAFF"
        assert "Monthly grievance log review" not in titles, \
            "Grievance log review (ADMIN) should NOT be visible to STAFF"

check(6, "Compliance role filter — staff sees only ALL-assigned items; no OFFICER/ADMIN items", check_6)


# Check 7 — PATCH /compliance/{id}/complete advances next_due
def check_7():
    with as_role("ADMIN", "president", "dave@chca.org") as c:
        items = c.get("/api/v1/compliance/").json()["items"]
        monthly_admin = [
            i for i in items
            if i["frequency"] == "monthly" and i["assigned_to_role"] == "ADMIN"
        ]
        assert monthly_admin, "No monthly ADMIN compliance items found"
        item = monthly_admin[0]
        old_due = item["next_due"]

        result = c.patch(
            f"/api/v1/compliance/{item['id']}/complete",
            json={"completed_date": "2026-02-22"},
        )
        assert result.status_code == 200, f"Expected 200, got {result.status_code}: {result.text}"
        data = result.json()
        assert data["status"] == "completed", f"Expected completed, got {data['status']}"
        assert data["last_completed"] == "2026-02-22"
        assert data["next_due"] != old_due, \
            f"next_due should have advanced from {old_due}, still {data['next_due']}"

check(7, "PATCH /compliance/{id}/complete — status=completed; next_due advanced for monthly item", check_7)


# Check 8 — POST /admin/users/{id}/role-detail allows ADMIN, blocks STAFF
def check_8():
    with as_role("ADMIN", "president", "dave@chca.org") as c:
        resp = c.post(
            "/api/v1/admin/users/newmember@chca.org/role-detail",
            json={
                "role_detail": "sectreasurer",
                "display_name": "New SecTreas",
                "email": "newmember@chca.org",
            },
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["role"] == "OFFICER", f"Expected OFFICER, got {data['role']}"
        assert data["role_detail"] == "sectreasurer"

    with as_role("STAFF", "staff", "staff4@chca.org") as c:
        staff_resp = c.post(
            "/api/v1/admin/users/anyone@chca.org/role-detail",
            json={"role_detail": "president"},
        )
        assert staff_resp.status_code == 403, \
            f"Staff should get 403, got {staff_resp.status_code}"

check(8, "POST /admin/users/{id}/role-detail — ADMIN sets role; STAFF gets 403", check_8)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n=== Smoke Test Results ===")
passed = sum(1 for _, r, _ in results if r == PASS)
failed = sum(1 for _, r, _ in results if r == FAIL)

for n, result, desc in results:
    icon = "✓" if result == PASS else "✗"
    print(f"  {icon} Check {n}: {result} — {desc}")

print(f"\n{passed}/{passed + failed} checks passed\n")

if failed > 0:
    sys.exit(1)
