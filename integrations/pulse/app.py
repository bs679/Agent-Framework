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

Phase 10 additions
------------------
- Rate limiting via slowapi (Redis-backed in production, memory in dev)
- CORS middleware restricted to known origins
- Security headers middleware (CSP, HSTS, etc.)
- Health check endpoints (/api/v1/health)
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from integrations.ai.router import AIRouter
from integrations.pulse.api.v1.admin import router as admin_router
from integrations.pulse.api.v1.agents import router as agents_router
# Phase 9a — President Officer Modules
from integrations.pulse.api.v1.board import router as board_router
from integrations.pulse.api.v1.compliance import router as compliance_router
from integrations.pulse.api.v1.grievances import router as grievances_router
from integrations.pulse.api.v1.health import router as health_router
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

# ---------------------------------------------------------------------------
# Rate limiter (slowapi — backed by Redis if available, memory otherwise)
# ---------------------------------------------------------------------------
_redis_url = os.environ.get("REDIS_URL", "")
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_redis_url if _redis_url else "memory://",
    default_limits=["100/minute"],
)

# ---------------------------------------------------------------------------
# CORS origins
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get(
    "CORS_ORIGINS",
    "tauri://localhost,http://localhost:5173,http://localhost:3000",
)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]


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


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Pulse — Agent Plane Integration",
    version="0.10.0",
    docs_url="/docs" if settings.agent_plane_enabled else None,
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted to known origins (Tauri desktop + localhost dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Only set HSTS if served over HTTPS
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# ---------------------------------------------------------------------------
# Correlation ID middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    """Attach a correlation ID to every request and response."""
    correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Health endpoints — always mounted (no auth, needed by monitoring)
app.include_router(health_router)

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


# ---------------------------------------------------------------------------
# Legacy liveness probe (kept for backwards compatibility)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_legacy() -> dict[str, str]:
    """Legacy liveness probe — use /api/v1/health instead."""
    return {
        "status": "ok",
        "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled",
    }
