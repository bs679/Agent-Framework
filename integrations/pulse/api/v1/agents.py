"""Agent-plane API endpoints for Pulse.

All endpoints live under ``/api/v1/agents/`` and require Azure AD JWT
authentication.  They are additive — no existing Pulse endpoints are
modified.

Context endpoint
----------------
GET /api/v1/agents/context uses the role-based context builder to return
different sections depending on the authenticated user's role:

  ADMIN (President)   → base + compliance + grievances + board + finance_summary + legislative
  OFFICER SecTreas    → base + compliance + finance (full detail) + minutes_pending
  OFFICER ExecSec     → base + compliance + scheduling + minutes (drafts)
  STAFF               → base + compliance only (no sensitive org data)

Compliance is always included but filtered so each role only sees items
assigned to their role or to ALL.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import (
    AgentContextResponse,
    CaptureRequest,
    CaptureResponse,
    CheckinRequest,
    CheckinResponse,
    CheckinStatusResponse,
    CheckinSlotStatus,
    SuggestedAction,
)
from integrations.pulse.core.auth import get_current_user_with_role
from integrations.pulse.core.context_builder import build_context
from integrations.pulse.core.database import get_db
from integrations.pulse.core.store import checkin_store

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# GET /api/v1/agents/context
# ---------------------------------------------------------------------------

@router.get("/context", response_model=AgentContextResponse)
async def get_agent_context(
    user: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> AgentContextResponse:
    """Return the daily context bundle for the authenticated user's agent.

    The bundle is assembled by the role-based context builder.  Each role
    receives only the sections appropriate for their access level:

    - Calendar events with executive-session keywords are sanitised.
    - Compliance items are filtered to the user's role.
    - Officer/admin sections are absent for STAFF users.
    """
    return build_context(
        owner_id=user["user_id"],
        role=user["role"],
        role_detail=user["role_detail"],
        db=db,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/agents/checkin
# ---------------------------------------------------------------------------

@router.post("/checkin", response_model=CheckinResponse)
async def post_agent_checkin(
    body: CheckinRequest,
    user: dict[str, Any] = Depends(get_current_user_with_role),
) -> CheckinResponse:
    """Accept a morning or evening check-in from an agent."""
    owner_id: str = user["user_id"]
    checkin_id = checkin_store.save(owner_id, body.model_dump())
    return CheckinResponse(status="accepted", checkin_id=checkin_id)


# ---------------------------------------------------------------------------
# GET /api/v1/agents/checkin/status
# ---------------------------------------------------------------------------

@router.get("/checkin/status", response_model=CheckinStatusResponse)
async def get_checkin_status(
    user: dict[str, Any] = Depends(get_current_user_with_role),
) -> CheckinStatusResponse:
    """Return today's morning/evening check-in status for the sidebar."""
    owner_id: str = user["user_id"]
    data = checkin_store.get_today_status(owner_id)
    return CheckinStatusResponse(
        morning=CheckinSlotStatus(**data["morning"]),
        evening=CheckinSlotStatus(**data["evening"]),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/agents/capture
# ---------------------------------------------------------------------------

@router.post("/capture", response_model=CaptureResponse)
async def post_capture(
    body: CaptureRequest,
    user: dict[str, Any] = Depends(get_current_user_with_role),
) -> CaptureResponse:
    """Quick-capture: Pulse sends raw note to agent for processing.

    In production this forwards to the agent plane for NLP processing.
    For now returns a heuristic-based suggestion.
    """
    content_lower = body.content.lower()

    # Simple heuristic routing until agent plane NLP is wired up
    if any(kw in content_lower for kw in ("follow up", "remind", "deadline", "due")):
        action = SuggestedAction.create_task
        details = f"Create task: {body.content}"
    elif any(kw in content_lower for kw in ("reply", "respond", "email")):
        action = SuggestedAction.reply_email
        details = f"Draft reply regarding: {body.content}"
    elif any(kw in content_lower for kw in ("remember", "note", "save")):
        action = SuggestedAction.add_to_memory
        details = f"Saved to agent memory: {body.content}"
    else:
        action = SuggestedAction.flag_for_review
        details = f"Flagged for review: {body.content}"

    return CaptureResponse(suggested_action=action, details=details)
