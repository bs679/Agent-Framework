"""Unit tests for the shared Docker status helper (provisioning/cli/docker_status).

Lives in the Pulse test tree so CI's single pytest invocation covers it.
The docker CLI is faked via monkeypatching run_docker.
"""

from __future__ import annotations

from provisioning.cli import docker_status


def _fake_run(rc: int, stdout: str = "", stderr: str = ""):
    return lambda args, timeout=10: (rc, stdout, stderr)


class TestContainerStatus:
    def test_running(self, monkeypatch):
        monkeypatch.setattr(docker_status, "run_docker", _fake_run(0, "true"))
        assert docker_status.container_status("openclaw-x") == "running"

    def test_stopped(self, monkeypatch):
        monkeypatch.setattr(docker_status, "run_docker", _fake_run(0, "false"))
        assert docker_status.container_status("openclaw-x") == "stopped"

    def test_missing_container(self, monkeypatch):
        monkeypatch.setattr(
            docker_status,
            "run_docker",
            _fake_run(1, "", "Error: No such object: openclaw-x"),
        )
        assert docker_status.container_status("openclaw-x") == "missing"

    def test_daemon_down_is_unavailable_not_missing(self, monkeypatch):
        monkeypatch.setattr(
            docker_status,
            "run_docker",
            _fake_run(
                1,
                "",
                "Cannot connect to the Docker daemon at unix:///var/run/docker.sock",
            ),
        )
        assert docker_status.container_status("openclaw-x") == "unavailable"

    def test_socket_permission_denied_is_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            docker_status,
            "run_docker",
            _fake_run(
                1,
                "",
                "permission denied while trying to connect to the Docker daemon socket",
            ),
        )
        assert docker_status.container_status("openclaw-x") == "unavailable"

    def test_cli_not_installed_is_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            docker_status,
            "run_docker",
            _fake_run(1, "", "docker not found — is Docker installed?"),
        )
        assert docker_status.container_status("openclaw-x") == "unavailable"


class TestContainerLogs:
    def test_merges_stdout_and_stderr_streams(self, monkeypatch):
        monkeypatch.setattr(
            docker_status,
            "run_docker",
            _fake_run(0, "out line 1\nout line 2", "err line 1"),
        )
        ok, lines = docker_status.container_logs("openclaw-x")
        assert ok is True
        assert lines == ["out line 1", "out line 2", "err line 1"]

    def test_failure_returns_stderr_message(self, monkeypatch):
        monkeypatch.setattr(
            docker_status, "run_docker", _fake_run(1, "", "no such container")
        )
        ok, lines = docker_status.container_logs("openclaw-x")
        assert ok is False
        assert lines == ["no such container"]


class TestRestart:
    def test_restart_ok(self, monkeypatch):
        monkeypatch.setattr(docker_status, "run_docker", _fake_run(0, "openclaw-x"))
        ok, message = docker_status.restart_container("openclaw-x")
        assert ok is True
        assert "openclaw-x" in message

    def test_restart_failure(self, monkeypatch):
        monkeypatch.setattr(
            docker_status, "run_docker", _fake_run(1, "", "daemon unreachable")
        )
        ok, message = docker_status.restart_container("openclaw-x")
        assert ok is False
        assert message == "daemon unreachable"
