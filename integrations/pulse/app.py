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

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response

from integrations.ai.router import AIRouter
from integrations.pulse.api.v1.admin import router as admin_router
from integrations.pulse.api.v1.agents import router as agents_router
# Phase 9a — President Officer Modules
from integrations.pulse.api.v1.board import router as board_router
from integrations.pulse.api.v1.compliance import router as compliance_router
from integrations.pulse.api.v1.grievances import router as grievances_router
from integrations.pulse.api.v1.legislative import router as legislative_router
from integrations.pulse.api.v1.research import router as research_router
# Phase 9b — Secretary/Treasurer + Executive Secretary Officer Modules
from integrations.pulse.api.v1.finance import router as finance_router
from integrations.pulse.api.v1.minutes_api import router as minutes_router
from integrations.pulse.api.v1.scheduling import router as scheduling_router
from integrations.pulse.core.config import get_settings
from integrations.pulse.core.database import init_db
from integrations.pulse.core.scheduler import create_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database and start background services on startup."""
    # Phase 9c: Initialize database (create tables + seed compliance data)
    init_db()

    # Initialize AIRouter — stored on app.state so route handlers can reach it
    ai_router = AIRouter()
    app.state.ai_router = ai_router
    health = await ai_router.health()
    for model, mdl_status in health.items():
        logger.info("[pulse] AI router — %s: %s", model, mdl_status)

    # Start grievance deadline monitoring scheduler (Phase 9a)
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("[pulse] Grievance deadline scheduler started.")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("[pulse] Grievance deadline scheduler stopped.")


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
    # Phase 9c — Compliance calendar and admin endpoints
    app.include_router(compliance_router)
    app.include_router(admin_router)

# Phase 9a — President Officer Module endpoints (always mounted)
app.include_router(grievances_router)
app.include_router(research_router)
app.include_router(legislative_router)
app.include_router(board_router)

# Phase 9b — Officer module routers (always mounted regardless of agent_plane flag)
app.include_router(finance_router)
app.include_router(minutes_router)
app.include_router(scheduling_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled"}
