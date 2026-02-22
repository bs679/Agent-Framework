"""Tests for the /api/v1/agents/* endpoints.

Uses FastAPI's TestClient with JWT auth mocked out via dependency overrides
defined in conftest.py.  Tests run against an in-memory SQLite DB.
"""

import pytest
from fastapi.testclient import TestClient

from integrations.pulse.core.store import checkin_store


# ── GET /api/v1/agents/context ─────────────────────────────────────

class TestContextEndpoint:
    def test_returns_200(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/agents/context")
        assert resp.status_code == 200

    def test_response_structure(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert data["owner_id"] == "dave@chca.org"
        assert "generated_at" in data
        assert "calendar" in data
        assert "tasks" in data
        assert "email" in data
        assert "compliance" in data

    def test_calendar_has_today_and_upcoming(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        assert "today" in data["calendar"]
        assert "upcoming_48h" in data["calendar"]

    def test_executive_session_sanitized(self, admin_client: TestClient) -> None:
        """The stub data includes an 'Executive Session - Board Review'
        event.  It must be sanitized in the API response."""
        data = admin_client.get("/api/v1/agents/context").json()
        today = data["calendar"]["today"]
        exec_events = [e for e in today if e["is_executive_session"]]
        assert len(exec_events) >= 1

        for evt in exec_events:
            assert evt["title"] == "Executive Session"
            assert evt["location"] is None
            assert evt["attendees_count"] == 0

    def test_non_executive_events_not_sanitized(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        today = data["calendar"]["today"]
        normal_events = [e for e in today if not e["is_executive_session"]]
        assert len(normal_events) >= 1
        for evt in normal_events:
            assert evt["title"] != "Executive Session"

    def test_tasks_structure(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        tasks = data["tasks"]
        assert "overdue" in tasks
        assert "due_today" in tasks
        assert "high_priority" in tasks
        assert isinstance(tasks["items"], list)

    def test_email_structure(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/context").json()
        email = data["email"]
        assert "unread_count" in email
        assert "urgent_count" in email


# ── POST /api/v1/agents/checkin ────────────────────────────────────

class TestCheckinEndpoint:
    def _morning_checkin(self) -> dict:
        return {
            "agent_id": "president-dave-a3f2",
            "checkin_type": "morning",
            "timestamp": "2026-02-21T07:02:00Z",
            "summary": "Good morning. 3 tasks due today, 1 overdue.",
            "alerts": [
                {
                    "type": "deadline",
                    "message": "Grievance deadline: Waterbury #24-117 — tomorrow",
                    "priority": "high",
                }
            ],
        }

    def test_accepts_morning_checkin(self, admin_client: TestClient) -> None:
        resp = admin_client.post("/api/v1/agents/checkin", json=self._morning_checkin())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert "checkin_id" in data

    def test_accepts_evening_checkin(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "checkin_type": "evening",
            "timestamp": "2026-02-21T17:00:00Z",
            "summary": "End of day. All tasks addressed.",
            "alerts": [],
        }
        resp = admin_client.post("/api/v1/agents/checkin", json=body)
        assert resp.status_code == 200

    def test_rejects_invalid_checkin_type(self, admin_client: TestClient) -> None:
        body = self._morning_checkin()
        body["checkin_type"] = "midnight"
        resp = admin_client.post("/api/v1/agents/checkin", json=body)
        assert resp.status_code == 422


# ── GET /api/v1/agents/checkin/status ──────────────────────────────

class TestCheckinStatusEndpoint:
    def test_empty_status(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/agents/checkin/status").json()
        assert data["morning"]["completed"] is False
        assert data["evening"]["completed"] is False

    def test_after_morning_checkin(self, admin_client: TestClient) -> None:
        admin_client.post(
            "/api/v1/agents/checkin",
            json={
                "agent_id": "president-dave-a3f2",
                "checkin_type": "morning",
                "timestamp": "2026-02-21T07:02:00Z",
                "summary": "Morning check-in.",
                "alerts": [],
            },
        )
        data = admin_client.get("/api/v1/agents/checkin/status").json()
        assert data["morning"]["completed"] is True
        assert data["morning"]["time"] == "07:02"
        assert data["evening"]["completed"] is False

    def test_after_both_checkins(self, admin_client: TestClient) -> None:
        admin_client.post(
            "/api/v1/agents/checkin",
            json={
                "agent_id": "president-dave-a3f2",
                "checkin_type": "morning",
                "timestamp": "2026-02-21T07:02:00Z",
                "summary": "AM",
                "alerts": [],
            },
        )
        admin_client.post(
            "/api/v1/agents/checkin",
            json={
                "agent_id": "president-dave-a3f2",
                "checkin_type": "evening",
                "timestamp": "2026-02-21T17:05:00Z",
                "summary": "PM",
                "alerts": [],
            },
        )
        data = admin_client.get("/api/v1/agents/checkin/status").json()
        assert data["morning"]["completed"] is True
        assert data["evening"]["completed"] is True
        assert data["evening"]["time"] == "17:05"


# ── POST /api/v1/agents/capture ────────────────────────────────────

class TestCaptureEndpoint:
    def test_task_suggestion(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "Follow up with Waterbury steward about grievance",
            "context": "manual",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggested_action"] == "create_task"

    def test_email_suggestion(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "Reply to the steward's email about scheduling",
            "context": "email",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        data = resp.json()
        assert data["suggested_action"] == "reply_email"

    def test_memory_suggestion(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "Remember that next meeting is on Tuesday",
            "context": "manual",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        data = resp.json()
        assert data["suggested_action"] == "add_to_memory"

    def test_flag_for_review_fallback(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "Interesting article about healthcare trends",
            "context": "manual",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        data = resp.json()
        assert data["suggested_action"] == "flag_for_review"

    def test_rejects_invalid_context(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "test",
            "context": "invalid",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        assert resp.status_code == 422

    def test_response_has_details(self, admin_client: TestClient) -> None:
        body = {
            "agent_id": "president-dave-a3f2",
            "content": "Follow up with Waterbury steward",
            "context": "manual",
        }
        resp = admin_client.post("/api/v1/agents/capture", json=body)
        data = resp.json()
        assert "details" in data
        assert len(data["details"]) > 0


# ── Health check ───────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
