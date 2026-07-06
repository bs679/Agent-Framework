"""Shared Docker container status inspection.

Used by both the ``aios planes status`` CLI command and the Pulse admin
dashboard endpoints so they report identical container state.

Status values
-------------
- ``running``      container exists and is running
- ``stopped``      container exists but is not running
- ``missing``      no container with that name
- ``unavailable``  the docker CLI is not installed or not responding
"""

from __future__ import annotations

import subprocess


def run_docker(args: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a docker command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", "docker not found — is Docker installed?"


def agent_container_name(agent_id: str) -> str:
    """Canonical container name for a provisioned agent."""
    return f"openclaw-{agent_id}"


def container_status(container_name: str) -> str:
    """Return the live status of a container: running/stopped/missing/unavailable."""
    rc, stdout, stderr = run_docker(
        ["inspect", "--format", "{{.State.Running}}", container_name]
    )
    if rc == 0:
        return "running" if stdout.strip().lower() == "true" else "stopped"
    if "docker not found" in stderr or "timed out" in stderr:
        return "unavailable"
    # docker responded but the container doesn't exist
    return "missing"


def container_logs(container_name: str, tail: int = 100) -> tuple[bool, list[str]]:
    """Return (ok, lines) with the last *tail* log lines of a container."""
    rc, stdout, stderr = run_docker(
        ["logs", "--tail", str(tail), container_name], timeout=15
    )
    if rc != 0:
        return False, [stderr or "could not read logs"]
    # docker logs writes app output to stdout; include stderr stream too if present
    return True, stdout.splitlines()


def restart_container(container_name: str) -> tuple[bool, str]:
    """Restart a container. Returns (ok, message)."""
    rc, stdout, stderr = run_docker(["restart", container_name], timeout=60)
    if rc != 0:
        return False, stderr or "restart failed"
    return True, f"{container_name} restarted"
