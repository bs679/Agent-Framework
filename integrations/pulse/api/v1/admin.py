"""Admin-only endpoints for Pulse.

All endpoints under /api/v1/admin/ require the ADMIN role.  Non-ADMIN
requests are rejected with 403 Forbidden.

Endpoints
---------
POST /api/v1/admin/users/{user_id}/role-detail
    Assign or update role + role_detail for a user profile.
    This is how Dave sets SecTreas vs ExecSec for the officer staff.

GET  /api/v1/admin/users/{user_id}
    Retrieve a user profile (ADMIN only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import RoleDetailRequest, UserProfileResponse
from integrations.pulse.core.auth import get_current_user_with_role
from integrations.pulse.core.database import get_db
from integrations.pulse.core.models import RoleDetail, UserProfile, UserRole

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Role validation helpers
# ---------------------------------------------------------------------------

_VALID_ROLE_DETAILS = {rd.value for rd in RoleDetail}
_VALID_ROLES = {r.value for r in UserRole}

# Automatic top-level role inference from role_detail
_ROLE_FROM_DETAIL: dict[str, str] = {
    "president": UserRole.ADMIN.value,
    "sectreasurer": UserRole.OFFICER.value,
    "execsecretary": UserRole.OFFICER.value,
    "staff": UserRole.STAFF.value,
}


def _require_admin(user: dict[str, Any]) -> None:
    """Raise 403 if the user is not ADMIN."""
    if user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires ADMIN role.",
        )


# ---------------------------------------------------------------------------
# POST /api/v1/admin/users/{user_id}/role-detail
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/role-detail",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def set_user_role_detail(
    user_id: str,
    body: RoleDetailRequest,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Assign or update a user's role_detail (and optionally role).

    If *role* is omitted in the request body, it is inferred from
    *role_detail* automatically:
      - president      → ADMIN
      - sectreasurer   → OFFICER
      - execsecretary  → OFFICER
      - staff          → STAFF

    Only ADMIN (Dave) can call this endpoint.
    """
    _require_admin(caller)

    # Validate role_detail
    if body.role_detail not in _VALID_ROLE_DETAILS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid role_detail {body.role_detail!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_ROLE_DETAILS))}"
            ),
        )

    # Determine top-level role
    if body.role:
        if body.role not in _VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid role {body.role!r}. "
                    f"Must be one of: {', '.join(sorted(_VALID_ROLES))}"
                ),
            )
        resolved_role = body.role
    else:
        resolved_role = _ROLE_FROM_DETAIL[body.role_detail]

    # Upsert user profile
    profile: UserProfile | None = (
        db.query(UserProfile)
        .filter(UserProfile.azure_user_id == user_id)
        .first()
    )

    if profile is None:
        profile = UserProfile(
            azure_user_id=user_id,
            role=resolved_role,
            role_detail=body.role_detail,
            display_name=body.display_name,
            email=body.email,
        )
        db.add(profile)
        action = "created"
    else:
        profile.role = resolved_role
        profile.role_detail = body.role_detail
        if body.display_name is not None:
            profile.display_name = body.display_name
        if body.email is not None:
            profile.email = body.email
        profile.updated_at = datetime.utcnow()
        action = "updated"

    db.commit()
    db.refresh(profile)

    return UserProfileResponse(
        user_id=profile.azure_user_id,
        role=profile.role,
        role_detail=profile.role_detail,
        display_name=profile.display_name,
        email=profile.email,
        message=f"User profile {action} successfully.",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users/{user_id}
# ---------------------------------------------------------------------------

@router.get(
    "/users/{user_id}",
    response_model=UserProfileResponse,
)
async def get_user_profile(
    user_id: str,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Retrieve a user's role profile.  ADMIN only."""
    _require_admin(caller)

    profile: UserProfile | None = (
        db.query(UserProfile)
        .filter(UserProfile.azure_user_id == user_id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profile found for user_id={user_id!r}.",
        )

    return UserProfileResponse(
        user_id=profile.azure_user_id,
        role=profile.role,
        role_detail=profile.role_detail,
        display_name=profile.display_name,
        email=profile.email,
        message="Profile retrieved.",
    )


# ---------------------------------------------------------------------------
# Agent monitoring — Phase 6 admin dashboard backend
#
# Cross-cutting rule: admin sees METRICS, never secrets. These endpoints
# expose registry metadata, container state, and heartbeat times only —
# no config contents, no memory, no env values.
# ---------------------------------------------------------------------------

from pydantic import BaseModel

from integrations.pulse.core.store import checkin_store
from provisioning.cli import docker_status
from provisioning.cli.registry import list_planes


class AgentSlotStatus(BaseModel):
    completed: bool = False
    time: str | None = None


class AgentStatusOut(BaseModel):
    agent_id: str
    owner: str
    role: str
    plane: str
    container: str  # running | stopped | missing | unavailable
    morning_checkin: AgentSlotStatus
    evening_checkin: AgentSlotStatus


class AgentListResponse(BaseModel):
    agents: list[AgentStatusOut]
    docker_available: bool


class AgentLogsResponse(BaseModel):
    agent_id: str
    lines: list[str]


class AgentActionResponse(BaseModel):
    agent_id: str
    ok: bool
    message: str


def _registered_agents() -> dict[str, dict[str, Any]]:
    """Flatten the plane registry into {agent_id: record}."""
    agents: dict[str, dict[str, Any]] = {}
    for plane in list_planes().values():
        for agent_id, record in plane.get("agents", {}).items():
            agents[agent_id] = record
    return agents


def _checkin_slots(agent_id: str, owner: str) -> tuple[AgentSlotStatus, AgentSlotStatus]:
    """Today's morning/evening heartbeat for an agent.

    Check-ins may be keyed by the agent slug (agent-token posts) or the
    owner identity (scheduler/owner posts) — merge both.
    """
    morning = AgentSlotStatus()
    evening = AgentSlotStatus()
    for key in (agent_id, owner):
        data = checkin_store.get_today_status(key)
        if not morning.completed and data["morning"]["completed"]:
            morning = AgentSlotStatus(
                completed=True, time=data["morning"].get("time")
            )
        if not evening.completed and data["evening"]["completed"]:
            evening = AgentSlotStatus(
                completed=True, time=data["evening"].get("time")
            )
    return morning, evening


@router.get("/agents", response_model=AgentListResponse)
async def list_agent_status(
    caller: dict[str, Any] = Depends(get_current_user_with_role),
) -> AgentListResponse:
    """List all registered agents with live container state and heartbeats."""
    _require_admin(caller)

    agents: list[AgentStatusOut] = []
    docker_available = True
    for agent_id, record in sorted(_registered_agents().items()):
        container = docker_status.container_status(
            docker_status.agent_container_name(agent_id)
        )
        if container == "unavailable":
            docker_available = False
        morning, evening = _checkin_slots(agent_id, record.get("owner", ""))
        agents.append(
            AgentStatusOut(
                agent_id=agent_id,
                owner=record.get("owner", ""),
                role=record.get("role", "standard"),
                plane=record.get("plane", ""),
                container=container,
                morning_checkin=morning,
                evening_checkin=evening,
            )
        )
    return AgentListResponse(agents=agents, docker_available=docker_available)


def _require_registered_agent(agent_id: str) -> None:
    """403 unless agent_id is in the registry — never touch arbitrary containers."""
    if agent_id not in _registered_agents():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id!r} is not registered.",
        )


@router.get("/agents/{agent_id}/logs", response_model=AgentLogsResponse)
async def get_agent_logs(
    agent_id: str,
    tail: int = 100,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
) -> AgentLogsResponse:
    """Last *tail* container log lines for a registered agent. ADMIN only."""
    _require_admin(caller)
    _require_registered_agent(agent_id)
    tail = max(1, min(tail, 1000))

    ok, lines = docker_status.container_logs(
        docker_status.agent_container_name(agent_id), tail=tail
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not read logs: {lines[0] if lines else 'unknown error'}",
        )
    return AgentLogsResponse(agent_id=agent_id, lines=lines)


@router.post("/agents/{agent_id}/restart", response_model=AgentActionResponse)
async def restart_agent(
    agent_id: str,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
) -> AgentActionResponse:
    """Restart a registered agent's container. ADMIN only."""
    _require_admin(caller)
    _require_registered_agent(agent_id)

    ok, message = docker_status.restart_container(
        docker_status.agent_container_name(agent_id)
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Restart failed: {message}",
        )
    return AgentActionResponse(agent_id=agent_id, ok=True, message=message)


# ---------------------------------------------------------------------------
# n8n workflow health — observability baseline (PROJECT_REVIEW P2 #10)
# ---------------------------------------------------------------------------

import os

import httpx


class N8nStatusResponse(BaseModel):
    enabled: bool
    reachable: bool = False
    sampled: int = 0
    succeeded: int = 0
    failed: int = 0
    success_rate: float | None = None  # over finished executions in the sample


async def _fetch_n8n_executions(url: str, api_key: str, limit: int = 50) -> list[dict]:
    """Fetch recent executions from the n8n public API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{url.rstrip('/')}/api/v1/executions",
            params={"limit": limit},
            headers={"X-N8N-API-KEY": api_key},
        )
        resp.raise_for_status()
        payload = resp.json()
    return payload.get("data", [])


@router.get("/n8n/status", response_model=N8nStatusResponse)
async def n8n_status(
    caller: dict[str, Any] = Depends(get_current_user_with_role),
) -> N8nStatusResponse:
    """Success rate of recent n8n workflow executions. ADMIN only.

    Reads N8N_API_URL + N8N_API_KEY; reports enabled=false when unset so
    the dashboard can hide the metric instead of erroring.
    """
    _require_admin(caller)

    url = os.environ.get("N8N_API_URL", "")
    api_key = os.environ.get("N8N_API_KEY", "")
    if not url or not api_key:
        return N8nStatusResponse(enabled=False)

    try:
        executions = await _fetch_n8n_executions(url, api_key)
    except Exception:
        return N8nStatusResponse(enabled=True, reachable=False)

    # n8n execution status values: success | error | crashed | canceled |
    # waiting | running — rate is computed over finished ones only
    succeeded = sum(1 for e in executions if e.get("status") == "success")
    failed = sum(1 for e in executions if e.get("status") in ("error", "crashed"))
    finished = succeeded + failed
    return N8nStatusResponse(
        enabled=True,
        reachable=True,
        sampled=len(executions),
        succeeded=succeeded,
        failed=failed,
        success_rate=round(succeeded / finished, 3) if finished else None,
    )
