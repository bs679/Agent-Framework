"""Health check endpoints for Pulse.

GET /api/v1/health        — lightweight liveness probe (no auth required)
GET /api/v1/health/full   — detailed component status (no auth required)

Both endpoints are intentionally unauthenticated so monitoring systems,
healthcheck scripts, and docker HEALTHCHECK instructions can use them
without managing tokens.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any

import httpx
from fastapi import APIRouter

from integrations.pulse.core.cache import redis_ping

router = APIRouter(prefix="/api/v1/health", tags=["health"])

_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_PULSE_API_URL = os.environ.get("PULSE_API_URL", "http://localhost:8000")
_POSTGRES_CONTAINER = os.environ.get("POSTGRES_CONTAINER", "postgres")
_POSTGRES_USER = os.environ.get("POSTGRES_USER", "pulse")

# Expected number of agent containers
_EXPECTED_AGENTS = int(os.environ.get("EXPECTED_AGENT_COUNT", "8"))

_AGENT_CONTAINERS = [
    "openclaw-president-dave",
    "openclaw-secretary-treasurer",
    "openclaw-executive-secretary",
    "openclaw-staff-4",
    "openclaw-staff-5",
    "openclaw-staff-6",
    "openclaw-staff-7",
    "openclaw-staff-8",
]


# ---------------------------------------------------------------------------
# Sub-checks
# ---------------------------------------------------------------------------

async def _check_database() -> str:
    """Return 'ok' or 'error' for PostgreSQL connectivity."""
    try:
        result = subprocess.run(
            ["docker", "exec", _POSTGRES_CONTAINER,
             "pg_isready", "-U", _POSTGRES_USER],
            capture_output=True,
            timeout=5,
        )
        return "ok" if result.returncode == 0 else "error"
    except Exception:
        return "error"


async def _check_ai_router() -> dict[str, str]:
    """Return per-model status from the AI router health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_PULSE_API_URL}/api/v1/ai/health")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "ollama": data.get("ollama", "error"),
                    "kimi_k2": data.get("kimi_k2", "disabled"),
                    "claude": data.get("claude", "disabled"),
                }
    except Exception:
        pass
    # Fallback: try Ollama directly
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{_OLLAMA_BASE_URL}/api/version")
            ollama = "ok" if resp.status_code == 200 else "error"
    except Exception:
        ollama = "error"
    return {"ollama": ollama, "kimi_k2": "unknown", "claude": "unknown"}


def _check_agents() -> dict[str, Any]:
    """Return agent container status summary."""
    running = 0
    degraded: list[str] = []

    for container in _AGENT_CONTAINERS:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format={{.State.Status}}", container],
                capture_output=True,
                text=True,
                timeout=5,
            )
            status = result.stdout.strip()
            if status == "running":
                running += 1
            else:
                degraded.append(container)
        except Exception:
            degraded.append(container)

    return {
        "running": running,
        "total": _EXPECTED_AGENTS,
        "degraded": degraded,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
@router.get("/")
async def health_liveness() -> dict[str, str]:
    """Lightweight liveness probe — returns 200 if process is alive.

    No auth required. Used by docker HEALTHCHECK and load balancers.
    """
    return {"status": "ok"}


@router.get("/full")
async def health_full() -> dict[str, Any]:
    """Detailed health status of all system components.

    Returns:
        status: "healthy" | "degraded" | "down"
        database: "ok" | "error"
        redis: "ok" | "disabled" | "error"
        ai_router: per-model status dict
        agents: running count and list of degraded containers

    No auth required — monitoring systems and healthcheck scripts need this.
    """
    # Run all checks concurrently
    db_status, redis_status, ai_status = await asyncio.gather(
        _check_database(),
        redis_ping(),
        _check_ai_router(),
    )
    agent_status = _check_agents()

    # Determine overall status
    critical_ok = (
        db_status == "ok"
        and agent_status["running"] == _EXPECTED_AGENTS
    )
    any_issue = (
        db_status != "ok"
        or redis_status == "error"
        or ai_status.get("ollama") != "ok"
        or agent_status["degraded"]
    )

    if not critical_ok:
        overall = "down"
    elif any_issue:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "ai_router": ai_status,
        "agents": agent_status,
    }
