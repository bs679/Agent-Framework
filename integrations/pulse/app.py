"""Pulse agent-plane FastAPI application.

Mount the agent-plane router alongside the existing Pulse app.  This
file can be used standalone for development or imported by the main
Pulse app to include the agent routes.

Usage (standalone):
    uvicorn integrations.pulse.app:app --reload --port 8000

Phase 9c additions
------------------
- /api/v1/compliance/* — shared compliance calendar (all 8 agents, role-filtered)
- /api/v1/admin/*      — ADMIN-only user role management
- Database initialised on startup via init_db()
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from integrations.pulse.api.v1.admin import router as admin_router
from integrations.pulse.api.v1.agents import router as agents_router
from integrations.pulse.api.v1.compliance import router as compliance_router
from integrations.pulse.core.config import get_settings
from integrations.pulse.core.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database (create tables + seed data) on startup."""
    init_db()
    yield


app = FastAPI(
    title="Pulse — Agent Plane Integration",
    version="0.9.0",
    docs_url="/docs" if settings.agent_plane_enabled else None,
    lifespan=lifespan,
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
    app.include_router(compliance_router)
    app.include_router(admin_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled"}
