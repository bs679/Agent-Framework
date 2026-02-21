"""Pulse agent-plane FastAPI application.

Mount the agent-plane router alongside the existing Pulse app.  This
file can be used standalone for development or imported by the main
Pulse app to include the agent routes.

Usage (standalone):
    uvicorn integrations.pulse.app:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI

from integrations.pulse.api.v1.agents import router as agents_router
from integrations.pulse.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Pulse — Agent Plane Integration",
    version="0.7.0",
    docs_url="/docs" if settings.agent_plane_enabled else None,
)

if settings.agent_plane_enabled:
    app.include_router(agents_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_plane": "enabled" if settings.agent_plane_enabled else "disabled"}
