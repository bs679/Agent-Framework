"""Pulse agent-plane FastAPI application.

Mount the agent-plane router alongside the existing Pulse app.  This
file can be used standalone for development or imported by the main
Pulse app to include the agent routes.

Usage (standalone):
    uvicorn integrations.pulse.app:app --reload --port 8000
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, Response

from integrations.pulse.api.v1.agents import router as agents_router
from integrations.pulse.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Pulse — Agent Plane Integration",
    version="0.7.0",
    docs_url="/docs" if settings.agent_plane_enabled else None,
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    """Attach a correlation ID to every request and response.

    Reads X-Correlation-ID from the incoming request if provided by the
    caller (e.g., the frontend or an n8n workflow), otherwise generates a
    new UUID4. The ID is echoed back in the response header so callers can
    correlate logs end-to-end.
    """
    correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


if settings.agent_plane_enabled:
    app.include_router(agents_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled"}
