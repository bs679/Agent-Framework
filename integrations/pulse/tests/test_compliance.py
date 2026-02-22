"""Tests for /api/v1/compliance/ endpoints.

Phase 9c — Part 2 tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestComplianceList:
    def test_admin_sees_compliance_items(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/compliance/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0

    def test_admin_sees_admin_and_all_items(self, admin_client: TestClient) -> None:
        """ADMIN sees ADMIN + ALL assigned items."""
        resp = admin_client.get("/api/v1/compliance/")
        data = resp.json()
        roles_seen = {i["assigned_to_role"] for i in data["items"]}
        assert "ALL" in roles_seen
        assert "ADMIN" in roles_seen
        # ADMIN should NOT see OFFICER-only items
        assert "OFFICER" not in roles_seen

    def test_officer_sees_officer_and_all_items(self, sectreasurer_client: TestClient) -> None:
        resp = sectreasurer_client.get("/api/v1/compliance/")
        data = resp.json()
        for item in data["items"]:
            assert item["assigned_to_role"] in ("OFFICER", "ALL"), (
                f"SecTreas should not see {item['assigned_to_role']}: {item['title']}"
            )

    def test_staff_sees_only_all_items(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/compliance/")
        data = resp.json()
        for item in data["items"]:
            assert item["assigned_to_role"] in ("STAFF", "ALL"), (
                f"Staff should not see {item['assigned_to_role']}: {item['title']}"
            )

    def test_items_have_required_fields(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/compliance/").json()
        for item in data["items"]:
            assert "id" in item
            assert "title" in item
            assert "category" in item
            assert "frequency" in item
            assert "assigned_to_role" in item
            assert "status" in item

    def test_grievance_log_review_admin_only(self, admin_client: TestClient) -> None:
        """Monthly grievance log review is ADMIN-only."""
        data = admin_client.get("/api/v1/compliance/").json()
        grievance_review = [
            i for i in data["items"]
            if "grievance log" in i["title"].lower()
        ]
        assert len(grievance_review) == 1
        assert grievance_review[0]["assigned_to_role"] == "ADMIN"

    def test_grievance_log_review_invisible_to_staff(self, staff_client: TestClient) -> None:
        data = staff_client.get("/api/v1/compliance/").json()
        grievance_items = [
            i for i in data["items"]
            if "grievance log" in i["title"].lower()
        ]
        assert len(grievance_items) == 0, (
            "Monthly grievance log review should not be visible to STAFF"
        )

    def test_lm2_invisible_to_staff(self, staff_client: TestClient) -> None:
        data = staff_client.get("/api/v1/compliance/").json()
        lm2_items = [i for i in data["items"] if "LM-2" in i["title"]]
        assert len(lm2_items) == 0, "LM-2 filing should not be visible to STAFF"

    def test_lm2_visible_to_officer(self, sectreasurer_client: TestClient) -> None:
        data = sectreasurer_client.get("/api/v1/compliance/").json()
        lm2_items = [i for i in data["items"] if "LM-2" in i["title"]]
        assert len(lm2_items) == 1, "LM-2 should be visible to OFFICER (SecTreas)"


class TestComplianceUpcoming:
    def test_upcoming_endpoint_returns_filtered_items(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/compliance/upcoming?days=365")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_upcoming_respects_days_parameter(self, admin_client: TestClient) -> None:
        """Items returned must have next_due within the requested window."""
        from datetime import date, timedelta
        resp = admin_client.get("/api/v1/compliance/upcoming?days=7")
        data = resp.json()
        today = date.today()
        horizon = today + timedelta(days=7)
        for item in data["items"]:
            if item["next_due"]:
                due = date.fromisoformat(item["next_due"])
                assert today <= due <= horizon, (
                    f"Item {item['title']} due {item['next_due']} is outside 7-day window"
                )

    def test_upcoming_defaults_to_30_days(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/compliance/upcoming")
        assert resp.status_code == 200

    def test_upcoming_invalid_days_rejected(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/compliance/upcoming?days=0")
        assert resp.status_code == 422


class TestComplianceComplete:
    def test_mark_admin_item_complete(self, admin_client: TestClient, db_session) -> None:
        """Mark an ADMIN-visible item as completed."""
        data = admin_client.get("/api/v1/compliance/").json()
        admin_items = [i for i in data["items"] if i["assigned_to_role"] == "ADMIN"]
        assert len(admin_items) > 0, "No ADMIN items available to complete"
        item_id = admin_items[0]["id"]

        resp = admin_client.patch(
            f"/api/v1/compliance/{item_id}/complete",
            json={"completed_date": "2026-02-22"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["id"] == item_id
        assert result["status"] == "completed"
        assert result["last_completed"] == "2026-02-22"
        assert result["next_due"] is not None  # Monthly item: should advance

    def test_mark_all_item_complete_as_staff(self, staff_client: TestClient) -> None:
        """Staff can mark ALL-assigned items complete."""
        data = staff_client.get("/api/v1/compliance/").json()
        all_items = [i for i in data["items"] if i["assigned_to_role"] == "ALL"]
        assert len(all_items) > 0
        item_id = all_items[0]["id"]

        resp = staff_client.patch(
            f"/api/v1/compliance/{item_id}/complete",
            json={},
        )
        assert resp.status_code == 200

    def test_staff_cannot_complete_officer_item(
        self, staff_client: TestClient, db_session
    ) -> None:
        """Staff trying to mark an OFFICER-only item returns 404."""
        from integrations.pulse.core.models import ComplianceItem

        officer_item = (
            db_session.query(ComplianceItem)
            .filter(ComplianceItem.assigned_to_role == "OFFICER")
            .first()
        )
        if officer_item is None:
            pytest.skip("No OFFICER items in test DB")

        resp = staff_client.patch(
            f"/api/v1/compliance/{officer_item.id}/complete",
            json={},
        )
        assert resp.status_code == 404

    def test_complete_nonexistent_item_returns_404(self, admin_client: TestClient) -> None:
        resp = admin_client.patch("/api/v1/compliance/99999/complete", json={})
        assert resp.status_code == 404

    def test_invalid_date_format_rejected(self, admin_client: TestClient, db_session) -> None:
        data = admin_client.get("/api/v1/compliance/").json()
        item_id = data["items"][0]["id"]
        resp = admin_client.patch(
            f"/api/v1/compliance/{item_id}/complete",
            json={"completed_date": "not-a-date"},
        )
        assert resp.status_code == 422
