"""Tests for the Phase 6 admin dashboard endpoints (/api/v1/admin/agents*).

Docker and the plane registry are faked via monkeypatching so tests run
without a Docker daemon or a provisioned .aios/registry.json.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from integrations.pulse.api.v1 import admin as admin_module
from integrations.pulse.core.store import checkin_store
from provisioning.cli import docker_status


_REGISTRY = {
    "chca-agents": {
        "name": "chca-agents",
        "agents": {
            "president-dave": {
                "id": "president-dave",
                "owner": "dave@chca.org",
                "role": "officer",
                "plane": "chca-agents",
            },
            "staff4-jordan": {
                "id": "staff4-jordan",
                "owner": "staff4@chca.org",
                "role": "standard",
                "plane": "chca-agents",
            },
        },
    }
}

_CONTAINER_STATES = {
    "openclaw-president-dave": "running",
    "openclaw-staff4-jordan": "stopped",
}


@pytest.fixture(autouse=True)
def fake_registry_and_docker(monkeypatch):
    monkeypatch.setattr(admin_module, "list_planes", lambda: _REGISTRY)
    monkeypatch.setattr(
        docker_status,
        "container_status",
        lambda name: _CONTAINER_STATES.get(name, "missing"),
    )
    checkin_store._checkins.clear()
    yield


class TestAgentList:
    def test_requires_admin(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/admin/agents")
        assert resp.status_code == 403

    def test_lists_registered_agents_with_container_state(
        self, admin_client: TestClient
    ) -> None:
        data = admin_client.get("/api/v1/admin/agents").json()
        assert data["docker_available"] is True
        agents = {a["agent_id"]: a for a in data["agents"]}
        assert set(agents) == {"president-dave", "staff4-jordan"}
        assert agents["president-dave"]["container"] == "running"
        assert agents["president-dave"]["owner"] == "dave@chca.org"
        assert agents["staff4-jordan"]["container"] == "stopped"

    def test_reports_docker_unavailable(self, admin_client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(
            docker_status, "container_status", lambda name: "unavailable"
        )
        data = admin_client.get("/api/v1/admin/agents").json()
        assert data["docker_available"] is False
        assert all(a["container"] == "unavailable" for a in data["agents"])

    def test_heartbeat_reflects_checkins_by_agent_slug(
        self, admin_client: TestClient
    ) -> None:
        checkin_store.save(
            "president-dave",
            {"checkin_type": "morning", "timestamp": "2026-07-06T07:02:00Z"},
        )
        data = admin_client.get("/api/v1/admin/agents").json()
        agents = {a["agent_id"]: a for a in data["agents"]}
        assert agents["president-dave"]["morning_checkin"]["completed"] is True
        assert agents["president-dave"]["evening_checkin"]["completed"] is False
        assert agents["staff4-jordan"]["morning_checkin"]["completed"] is False

    def test_heartbeat_reflects_checkins_by_owner_id(
        self, admin_client: TestClient
    ) -> None:
        checkin_store.save(
            "dave@chca.org",
            {"checkin_type": "evening", "timestamp": "2026-07-06T17:05:00Z"},
        )
        data = admin_client.get("/api/v1/admin/agents").json()
        agents = {a["agent_id"]: a for a in data["agents"]}
        assert agents["president-dave"]["evening_checkin"]["completed"] is True


class TestAgentLogs:
    def test_requires_admin(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/admin/agents/president-dave/logs")
        assert resp.status_code == 403

    def test_unregistered_agent_is_404(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/admin/agents/evil-container/logs")
        assert resp.status_code == 404

    def test_returns_log_lines(self, admin_client: TestClient, monkeypatch) -> None:
        captured: dict = {}

        def fake_logs(name, tail=100):
            captured["name"] = name
            captured["tail"] = tail
            return True, ["line one", "line two"]

        monkeypatch.setattr(docker_status, "container_logs", fake_logs)
        resp = admin_client.get("/api/v1/admin/agents/president-dave/logs?tail=50")
        assert resp.status_code == 200
        assert resp.json()["lines"] == ["line one", "line two"]
        assert captured == {"name": "openclaw-president-dave", "tail": 50}

    def test_tail_is_clamped(self, admin_client: TestClient, monkeypatch) -> None:
        captured: dict = {}

        def fake_logs(name, tail=100):
            captured["tail"] = tail
            return True, []

        monkeypatch.setattr(docker_status, "container_logs", fake_logs)
        admin_client.get("/api/v1/admin/agents/president-dave/logs?tail=99999")
        assert captured["tail"] == 1000

    def test_docker_failure_is_502(self, admin_client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(
            docker_status, "container_logs", lambda name, tail=100: (False, ["boom"])
        )
        resp = admin_client.get("/api/v1/admin/agents/president-dave/logs")
        assert resp.status_code == 502


class TestAgentRestart:
    def test_requires_admin(self, staff_client: TestClient) -> None:
        resp = staff_client.post("/api/v1/admin/agents/president-dave/restart")
        assert resp.status_code == 403

    def test_unregistered_agent_is_404(self, admin_client: TestClient) -> None:
        resp = admin_client.post("/api/v1/admin/agents/evil-container/restart")
        assert resp.status_code == 404

    def test_restart_success(self, admin_client: TestClient, monkeypatch) -> None:
        captured: dict = {}

        def fake_restart(name):
            captured["name"] = name
            return True, f"{name} restarted"

        monkeypatch.setattr(docker_status, "restart_container", fake_restart)
        resp = admin_client.post("/api/v1/admin/agents/president-dave/restart")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert captured["name"] == "openclaw-president-dave"

    def test_restart_failure_is_502(self, admin_client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(
            docker_status, "restart_container", lambda name: (False, "no daemon")
        )
        resp = admin_client.post("/api/v1/admin/agents/president-dave/restart")
        assert resp.status_code == 502


class TestN8nStatus:
    def test_requires_admin(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/admin/n8n/status")
        assert resp.status_code == 403

    def test_disabled_when_unconfigured(self, admin_client: TestClient, monkeypatch) -> None:
        monkeypatch.delenv("N8N_API_URL", raising=False)
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        data = admin_client.get("/api/v1/admin/n8n/status").json()
        assert data == {
            "enabled": False,
            "reachable": False,
            "sampled": 0,
            "succeeded": 0,
            "failed": 0,
            "success_rate": None,
        }

    def test_success_rate_over_finished_executions(
        self, admin_client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("N8N_API_URL", "http://n8n.local:5678")
        monkeypatch.setenv("N8N_API_KEY", "test-key")

        async def fake_fetch(url, api_key, limit=50):
            assert url == "http://n8n.local:5678"
            assert api_key == "test-key"
            return [
                {"status": "success"},
                {"status": "success"},
                {"status": "success"},
                {"status": "error"},
                {"status": "canceled"},  # terminal — counts as a failure
                {"status": "running"},   # unfinished — excluded from the rate
                {"status": "waiting"},   # unfinished — excluded from the rate
            ]

        monkeypatch.setattr(admin_module, "_fetch_n8n_executions", fake_fetch)
        data = admin_client.get("/api/v1/admin/n8n/status").json()
        assert data["enabled"] is True
        assert data["reachable"] is True
        assert data["sampled"] == 7
        assert data["succeeded"] == 3
        assert data["failed"] == 2
        assert data["success_rate"] == 0.6

    def test_unreachable_n8n_is_reported_not_500(
        self, admin_client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("N8N_API_URL", "http://n8n.local:5678")
        monkeypatch.setenv("N8N_API_KEY", "test-key")

        async def fake_fetch(url, api_key, limit=50):
            raise ConnectionError("refused")

        monkeypatch.setattr(admin_module, "_fetch_n8n_executions", fake_fetch)
        data = admin_client.get("/api/v1/admin/n8n/status").json()
        assert data["enabled"] is True
        assert data["reachable"] is False
