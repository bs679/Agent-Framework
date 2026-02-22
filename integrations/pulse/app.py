"""Pulse agent-plane FastAPI application.

Mount the agent-plane router alongside the existing Pulse app.  This
file can be used standalone for development or imported by the main
Pulse app to include the agent routes.

Usage (standalone):
    uvicorn integrations.pulse.app:app --reload --port 8000
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response

from integrations.ai.router import AIRouter
from integrations.pulse.api.v1.agents import router as agents_router
from integrations.pulse.api.v1.board import router as board_router
from integrations.pulse.api.v1.grievances import router as grievances_router
from integrations.pulse.api.v1.legislative import router as legislative_router
from integrations.pulse.api.v1.research import router as research_router
from integrations.pulse.core.config import get_settings
from integrations.pulse.core.scheduler import create_scheduler
from integrations.pulse.db.session import Base, engine

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Create all tables on startup (idempotent — safe when Alembic is also used)
# ---------------------------------------------------------------------------
def _ensure_tables() -> None:
    """Create tables that don't exist yet.

    In production, prefer running ``alembic upgrade head`` before starting the
    app. This call is a dev-mode safety net so the app is usable without a
    manual migration step.
    """
    import integrations.pulse.db.models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Application lifespan — start/stop the background scheduler
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Ensure DB tables exist (safe no-op if Alembic already ran)
    _ensure_tables()

    # Initialize AIRouter — stored on app.state so route handlers can reach it
    ai_router = AIRouter()
    app.state.ai_router = ai_router
    health = await ai_router.health()
    for model, mdl_status in health.items():
        logger.info("[pulse] AI router — %s: %s", model, mdl_status)

    # Start grievance deadline monitoring scheduler
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

# Phase 9a — President Officer Modules
app.include_router(grievances_router)
app.include_router(research_router)
app.include_router(legislative_router)
app.include_router(board_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled"}
