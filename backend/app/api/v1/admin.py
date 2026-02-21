"""Admin API endpoints.

All endpoints require ADMIN role JWT.
Privacy: No endpoint ever returns private config fields, memory contents, or secrets.

Routes:
  GET  /api/v1/admin/plane              — full plane overview
  GET  /api/v1/admin/agents/{id}/logs   — filtered log tail
  POST /api/v1/admin/agents/{id}/restart — restart container
  DELETE /api/v1/admin/agents/{id}       — remove container (preserves files)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...middleware.auth import require_admin
from ...models.admin import (
    ErrorResponse,
    LogResponse,
    PlaneResponse,
    RemoveRequest,
    RemoveResponse,
    RestartResponse,
)
from ...services.agent_service import (
    get_agent_logs,
    get_all_agents,
    remove_agent,
    restart_agent,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/plane",
    response_model=PlaneResponse,
    responses={403: {"model": ErrorResponse}},
)
def get_plane_status(user: dict = Depends(require_admin)):
    """Return the full plane overview with all agents.

    Never includes private fields — serialization is enforced
    by the AgentInfo/ConfigSummary models.
    """
    agents = get_all_agents()
    return PlaneResponse(
        plane_name="chca-agents",
        last_updated=datetime.now(timezone.utc),
        agents=agents,
    )


@router.get(
    "/agents/{agent_id}/logs",
    response_model=LogResponse,
    responses={403: {"model": ErrorResponse}},
)
def get_logs(
    agent_id: str,
    tail: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(require_admin),
):
    """Return last N log lines for an agent.

    Lines containing SECRET, KEY, TOKEN, or PASSWORD are replaced
    with '[sensitive -- not shown]'.
    """
    lines = get_agent_logs(agent_id, tail=tail)
    return LogResponse(agent_id=agent_id, lines=lines)


@router.post(
    "/agents/{agent_id}/restart",
    response_model=RestartResponse,
    responses={403: {"model": ErrorResponse}},
)
def restart(agent_id: str, user: dict = Depends(require_admin)):
    """Restart an agent's container. Returns new status after health check."""
    agent_status, health, message = restart_agent(agent_id)
    return RestartResponse(
        agent_id=agent_id,
        status=agent_status,
        health=health,
        message=message,
    )


@router.delete(
    "/agents/{agent_id}",
    response_model=RemoveResponse,
    responses={403: {"model": ErrorResponse}},
)
def remove(
    agent_id: str,
    body: RemoveRequest,
    user: dict = Depends(require_admin),
):
    """Remove an agent's container.

    Requires body: {"confirm": true, "agent_id": "..."} — double-check
    prevents accidents. Stops and removes the container but does NOT
    delete config or memory files.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required: set confirm to true",
        )
    if body.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent ID in body must match URL parameter",
        )

    removed, message = remove_agent(agent_id)
    return RemoveResponse(agent_id=agent_id, removed=removed, message=message)
