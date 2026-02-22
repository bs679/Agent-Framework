"""Tests for role-based context bundle.

Verifies that each role receives exactly the sections it should — and
does NOT receive sections from other roles.

Phase 9c — Part 1 & 3 tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestAdminContext:
    """ADMIN (President) should receive all officer-plus sections."""

    def test_admin_has_grievances(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert data["role"] == "ADMIN"
        assert data["role_detail"] == "president"
        assert data["grievances"] is not None
        assert "open_count" in data["grievances"]

    def test_admin_has_board(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert data["board"] is not None
        assert "next_meeting_date" in data["board"]

    def test_admin_has_finance_summary_not_detail(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        # ADMIN gets summary (count only), NOT full finance detail
        assert data["finance_summary"] is not None
        assert "pending_disbursements" in data["finance_summary"]
        # Full finance detail (with amounts) should be absent
        assert data["finance"] is None

    def test_admin_has_legislative(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert data["legislative"] is not None
        assert "tracked_bills" in data["legislative"]

    def test_admin_has_compliance(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert data["compliance"] is not None
        assert "items_due_30d" in data["compliance"]
        assert "overdue_count" in data["compliance"]

    def test_admin_has_no_officer_only_sections(self, admin_client: TestClient) -> None:
        """ADMIN should not have SecTreas or ExecSec sections."""
        data = admin_client.get("/api/v1/agents/context").json()
        # SecTreas-only
        assert data["finance"] is None
        assert data["minutes_pending"] is None
        # ExecSec-only
        assert data["scheduling"] is None
        assert data["minutes"] is None


class TestSecTreasContext:
    """OFFICER / SecTreas gets finance detail + minutes pending, not grievances."""

    def test_sectreasurer_has_finance_detail(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/agents/context").json()
        assert data["role"] == "OFFICER"
        assert data["role_detail"] == "sectreasurer"
        assert data["finance"] is not None
        assert "pending_amount_usd" in data["finance"]
        assert "dues_collected_mtd" in data["finance"]

    def test_sectreasurer_has_minutes_pending(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/agents/context").json()
        assert data["minutes_pending"] is not None
        assert "pending_approval_count" in data["minutes_pending"]

    def test_sectreasurer_has_compliance(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/agents/context").json()
        assert data["compliance"] is not None

    def test_sectreasurer_has_no_admin_sections(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/agents/context").json()
        assert data["grievances"] is None
        assert data["board"] is None
        assert data["finance_summary"] is None
        assert data["legislative"] is None

    def test_sectreasurer_has_no_execsec_sections(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/agents/context").json()
        assert data["scheduling"] is None
        assert data["minutes"] is None


class TestExecSecContext:
    """OFFICER / ExecSec gets scheduling + minutes drafts, not finance."""

    def test_execsec_has_scheduling(self, execsec_client: TestClient) -> None:
        data = execsec_client.get("/api/v1/agents/context").json()
        assert data["role"] == "OFFICER"
        assert data["role_detail"] == "execsecretary"
        assert data["scheduling"] is not None
        assert "pending_scheduling_requests" in data["scheduling"]

    def test_execsec_has_minutes_drafts(self, execsec_client: TestClient) -> None:
        data = execsec_client.get("/api/v1/agents/context").json()
        assert data["minutes"] is not None
        assert "drafts_in_progress" in data["minutes"]

    def test_execsec_has_compliance(self, execsec_client: TestClient) -> None:
        data = execsec_client.get("/api/v1/agents/context").json()
        assert data["compliance"] is not None

    def test_execsec_has_no_admin_sections(self, execsec_client: TestClient) -> None:
        data = execsec_client.get("/api/v1/agents/context").json()
        assert data["grievances"] is None
        assert data["board"] is None
        assert data["finance_summary"] is None
        assert data["legislative"] is None

    def test_execsec_has_no_finance_sections(self, execsec_client: TestClient) -> None:
        data = execsec_client.get("/api/v1/agents/context").json()
        assert data["finance"] is None
        assert data["minutes_pending"] is None


class TestStaffContext:
    """STAFF receives ONLY base context — no sensitive org data."""

    def test_staff_returns_200(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/agents/context")
        assert resp.status_code == 200

    def test_staff_has_base_sections(self, staff_client: TestClient) -> None:
        data = staff_client.get("/api/v1/agents/context").json()
        assert data["role"] == "STAFF"
        assert "calendar" in data
        assert "tasks" in data
        assert "email" in data
        assert "compliance" in data

    def test_staff_has_no_privileged_sections(self, staff_client: TestClient) -> None:
        data = staff_client.get("/api/v1/agents/context").json()
        # No admin sections
        assert data["grievances"] is None
        assert data["board"] is None
        assert data["finance_summary"] is None
        assert data["legislative"] is None
        # No officer sections
        assert data["finance"] is None
        assert data["minutes_pending"] is None
        assert data["scheduling"] is None
        assert data["minutes"] is None

    def test_staff_compliance_excludes_financial_items(self, staff_client: TestClient) -> None:
        """Staff should only see ALL-assigned compliance items, not OFFICER/ADMIN."""
        # Get the full compliance list as staff
        resp = staff_client.get("/api/v1/compliance/")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            # Staff sees STAFF or ALL items only
            assert item["assigned_to_role"] in ("STAFF", "ALL"), (
                f"Staff should not see item assigned to {item['assigned_to_role']}: "
                f"{item['title']}"
            )
