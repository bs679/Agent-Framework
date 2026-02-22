"""
AI routing API endpoints — health checks and routing introspection.

These endpoints let the frontend and CLI inspect the AI routing layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/health")
async def ai_health(request: Request):
    """Return health status of all configured AI model endpoints."""
    ai_router = request.app.state.ai_router
    return await ai_router.health()


@router.get("/routing")
async def ai_routing_table(request: Request):
    """Return the full routing table for introspection."""
    ai_router = request.app.state.ai_router
    routing = ai_router.config.get("routing", {})

    table = []
    for task_type, cfg in sorted(routing.items()):
        table.append(
            {
                "task_type": task_type,
                "model": cfg["model"],
                "sensitive": cfg["sensitive"],
                "fallback": cfg.get("fallback"),
                "description": cfg.get("description", ""),
            }
        )
    return {"routing": table}
