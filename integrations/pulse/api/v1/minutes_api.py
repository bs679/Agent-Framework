"""Minutes workflow API — Executive Secretary officer capability.

Endpoints at /api/v1/minutes/:

  POST /generate-draft          — AI-generated draft via AIRouter (minutes_draft → Ollama)
  GET  /                        — list minutes (filter by status and meeting)
  GET  /{id}                    — full detail with content_md
  PATCH /{id}                   — update content_md (ExecSec editing draft)
  POST /{id}/submit-for-approval — changes status, creates SecTreas task
  POST /{id}/approve            — OFFICER only, must be different person than drafter

Executive session rule:
  If executive_session_flag == true, content_md is encrypted at rest using
  Fernet symmetric encryption and only visible to OFFICER role.

AI routing:
  minutes_draft task → sensitive=True → always routes to Ollama (local only).
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from integrations.ai.router import AIRouter
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.roles import _has_officer_role, require_officer
from integrations.pulse.db.models.minutes import MeetingMinutes, PulseTask
from integrations.pulse.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/minutes", tags=["minutes"])

# ---------------------------------------------------------------------------
# Encryption helpers for executive session content
# ---------------------------------------------------------------------------

_EXEC_SESSION_FERNET_KEY_ENV = "EXEC_SESSION_FERNET_KEY"

# Process-level cache: generated once per process start if env var not set.
# Ensures encrypt/decrypt use the same key within a running process.
# Production MUST set EXEC_SESSION_FERNET_KEY so the key survives restarts.
_fernet_instance: "Fernet | None" = None  # type: ignore[name-defined]


def _get_fernet():
    """Return the process-level Fernet instance.

    Reads EXEC_SESSION_FERNET_KEY from the environment. If not set, generates
    a random key once and caches it for the lifetime of the process (dev/test
    only — NOT suitable for production since data won't survive restarts).
    """
    global _fernet_instance
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "cryptography package required for executive session encryption. "
            "pip install cryptography"
        ) from exc

    if _fernet_instance is not None:
        return _fernet_instance

    key_b64 = os.environ.get(_EXEC_SESSION_FERNET_KEY_ENV, "")
    if not key_b64:
        logger.warning(
            "EXEC_SESSION_FERNET_KEY not set — using ephemeral key. "
            "Set this env var in production so encrypted minutes survive restarts."
        )
        key = Fernet.generate_key()
    else:
        key = key_b64.encode()

    _fernet_instance = Fernet(key)
    return _fernet_instance


def _encrypt_content(plaintext: str) -> str:
    """Encrypt content_md for executive session minutes. Returns base64 string."""
    f = _get_fernet()
    encrypted_bytes = f.encrypt(plaintext.encode("utf-8"))
    return base64.b64encode(encrypted_bytes).decode("ascii")


def _decrypt_content(ciphertext_b64: str) -> str:
    """Decrypt executive session content_md. Raises on key mismatch."""
    f = _get_fernet()
    encrypted_bytes = base64.b64decode(ciphertext_b64.encode("ascii"))
    return f.decrypt(encrypted_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class GenerateDraftRequest(BaseModel):
    board_meeting_id: Optional[int] = None
    agenda_items: list[str]


class MinutesPatch(BaseModel):
    content_md: Optional[str] = None


class MinutesOut(BaseModel):
    id: int
    board_meeting_id: Optional[int]
    status: str
    content_md: Optional[str]
    template_used: Optional[str]
    executive_session_flag: bool
    drafted_by: str
    draft_at: str
    approved_by: Optional[str]
    approved_at: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ai_router: AIRouter | None = None


def _get_ai_router() -> AIRouter:
    global _ai_router
    if _ai_router is None:
        _ai_router = AIRouter()
    return _ai_router


def _dt_str(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _minutes_out(m: MeetingMinutes, user: dict[str, Any]) -> MinutesOut:
    """Serialize MeetingMinutes, respecting exec-session visibility rule."""
    content: str | None = None

    if m.content_md is not None:
        if m.executive_session_flag:
            if _has_officer_role(user):
                try:
                    content = _decrypt_content(m.content_md)
                except Exception:
                    content = "[Decryption error — contact system administrator]"
            else:
                # Non-officer: content redacted
                content = None
        else:
            content = m.content_md

    return MinutesOut(
        id=m.id,
        board_meeting_id=m.board_meeting_id,
        status=m.status,
        content_md=content,
        template_used=m.template_used,
        executive_session_flag=m.executive_session_flag,
        drafted_by=m.drafted_by,
        draft_at=_dt_str(m.draft_at) or "",
        approved_by=m.approved_by,
        approved_at=_dt_str(m.approved_at),
    )


def _is_exec_session_meeting(board_meeting_id: int | None, db: Session) -> bool:
    """Return True if the referenced board meeting is an executive session."""
    if board_meeting_id is None:
        return False
    from integrations.pulse.db.models.minutes import BoardMeeting
    bm = db.query(BoardMeeting).filter(BoardMeeting.id == board_meeting_id).first()
    return bool(bm and bm.type == "executive_session")


# ---------------------------------------------------------------------------
# POST /api/v1/minutes/generate-draft
# ---------------------------------------------------------------------------


@router.post("/generate-draft", response_model=MinutesOut, status_code=201)
async def generate_draft(
    body: GenerateDraftRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MinutesOut:
    """Generate a formal minutes draft via AIRouter.

    task="minutes_draft" is marked sensitive=True in ai-routing.yaml, so the
    router always sends this to Ollama. The minutes content never leaves the
    local network.
    """
    agenda_str = "\n".join(f"- {item}" for item in body.agenda_items)

    prompt = (
        "Generate a formal meeting minutes template for a union executive board meeting. "
        f"Agenda items:\n{agenda_str}\n\n"
        "Include: call to order, attendance, approval of previous minutes, "
        "each agenda item as a section, good of the order, adjournment. "
        "Use formal minutes style. Leave [ACTION RECORDED HERE] placeholders "
        "where specific actions or votes were taken."
    )

    ai = _get_ai_router()
    try:
        response = await ai.complete(task="minutes_draft", prompt=prompt)
        draft_content = response.text
        logger.info(
            "minutes_draft generated: routed_to=%s model=%s",
            response.routed_to,
            response.model_used,
        )
    except Exception as exc:
        logger.error("AI draft generation failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="AI draft generation unavailable. Check Ollama is running.",
        ) from exc

    exec_flag = _is_exec_session_meeting(body.board_meeting_id, db)
    now = datetime.now(timezone.utc)

    # Encrypt content if executive session
    stored_content = _encrypt_content(draft_content) if exec_flag else draft_content

    m = MeetingMinutes(
        board_meeting_id=body.board_meeting_id,
        status="draft",
        content_md=stored_content,
        template_used="ai_generated",
        executive_session_flag=exec_flag,
        drafted_by=user["user_id"],
        draft_at=now,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _minutes_out(m, user)


# ---------------------------------------------------------------------------
# GET /api/v1/minutes
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[MinutesOut])
async def list_minutes(
    status_filter: Optional[str] = Query(None, alias="status"),
    board_meeting_id: Optional[int] = Query(None),
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MinutesOut]:
    q = db.query(MeetingMinutes)
    if status_filter:
        q = q.filter(MeetingMinutes.status == status_filter)
    if board_meeting_id is not None:
        q = q.filter(MeetingMinutes.board_meeting_id == board_meeting_id)
    rows = q.order_by(MeetingMinutes.draft_at.desc()).all()
    return [_minutes_out(m, user) for m in rows]


# ---------------------------------------------------------------------------
# GET /api/v1/minutes/{id}
# ---------------------------------------------------------------------------


@router.get("/{minutes_id}", response_model=MinutesOut)
async def get_minutes(
    minutes_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MinutesOut:
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == minutes_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Minutes not found")
    return _minutes_out(m, user)


# ---------------------------------------------------------------------------
# PATCH /api/v1/minutes/{id}
# ---------------------------------------------------------------------------


@router.patch("/{minutes_id}", response_model=MinutesOut)
async def update_minutes(
    minutes_id: int,
    body: MinutesPatch,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MinutesOut:
    """Update content_md of a draft minutes document (ExecSec editing)."""
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == minutes_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Minutes not found")
    if m.status not in ("draft",):
        raise HTTPException(
            status_code=409,
            detail=f"Minutes in '{m.status}' status cannot be edited. Only 'draft' status allows editing.",
        )

    if m.drafted_by != user["user_id"] and not _has_officer_role(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the drafter or an officer may edit draft minutes.",
        )

    if body.content_md is not None:
        stored = _encrypt_content(body.content_md) if m.executive_session_flag else body.content_md
        m.content_md = stored

    db.commit()
    db.refresh(m)
    return _minutes_out(m, user)


# ---------------------------------------------------------------------------
# POST /api/v1/minutes/{id}/submit-for-approval
# ---------------------------------------------------------------------------


@router.post("/{minutes_id}/submit-for-approval", response_model=MinutesOut)
async def submit_for_approval(
    minutes_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MinutesOut:
    """Submit minutes for SecTreas approval.

    Changes status to pending_approval and creates a Pulse task assigned to
    SecTreas for review.
    """
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == minutes_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Minutes not found")
    if m.status != "draft":
        raise HTTPException(
            status_code=409,
            detail=f"Only 'draft' minutes can be submitted for approval. Current status: '{m.status}'",
        )

    m.status = "pending_approval"

    # Create a task in Pulse assigned to SecTreas for review
    task = PulseTask(
        title=f"Review minutes for approval (ID: {m.id})",
        description=(
            f"Meeting minutes #{m.id} have been submitted for review and approval. "
            f"Drafted by: {m.drafted_by}. "
            "Please review and either approve or return for revision."
        ),
        assigned_to="sectreas",  # SecTreas role identifier
        created_by=user["user_id"],
        created_at=datetime.now(timezone.utc),
        status="open",
        related_object=f"minutes:{m.id}",
    )
    db.add(task)
    db.commit()
    db.refresh(m)

    logger.info(
        "Minutes %d submitted for approval by %s — task created for SecTreas",
        m.id,
        user["user_id"],
    )
    return _minutes_out(m, user)


# ---------------------------------------------------------------------------
# POST /api/v1/minutes/{id}/approve
# ---------------------------------------------------------------------------


@router.post("/{minutes_id}/approve", response_model=MinutesOut)
async def approve_minutes(
    minutes_id: int,
    user: dict[str, Any] = Depends(require_officer),
    db: Session = Depends(get_db),
) -> MinutesOut:
    """Approve minutes — OFFICER role only, must not be the drafter.

    SecTreas retains final approval authority (enforced at role level).
    """
    m = db.query(MeetingMinutes).filter(MeetingMinutes.id == minutes_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Minutes not found")
    if m.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Only 'pending_approval' minutes can be approved. Current status: '{m.status}'",
        )

    # Approver must be a different person than the drafter
    if user["user_id"] == m.drafted_by:
        raise HTTPException(
            status_code=403,
            detail="The drafter cannot approve their own minutes. A different officer must approve.",
        )

    now = datetime.now(timezone.utc)
    m.status = "approved"
    m.approved_by = user["user_id"]
    m.approved_at = now

    # Mark the related SecTreas task as completed
    task = (
        db.query(PulseTask)
        .filter(
            PulseTask.related_object == f"minutes:{m.id}",
            PulseTask.status == "open",
        )
        .first()
    )
    if task:
        task.status = "completed"

    db.commit()
    db.refresh(m)
    logger.info("Minutes %d approved by %s", m.id, user["user_id"])
    return _minutes_out(m, user)


# ---------------------------------------------------------------------------
# Context bundle helper — used by agents context endpoint
# ---------------------------------------------------------------------------


def build_scheduling_context(db: Session) -> dict[str, Any]:
    """Build the 'scheduling' section for ExecSec agent context bundle."""
    from integrations.pulse.db.models.minutes import PulseTask

    drafts_in_progress = (
        db.query(MeetingMinutes)
        .filter(MeetingMinutes.status == "draft")
        .count()
    )
    pending_approval = (
        db.query(MeetingMinutes)
        .filter(MeetingMinutes.status == "pending_approval")
        .count()
    )
    pending_requests = (
        db.query(PulseTask)
        .filter(PulseTask.assigned_to == "execsec", PulseTask.status == "open")
        .count()
    )

    return {
        "pending_requests": pending_requests,
        "minutes_drafts_in_progress": drafts_in_progress,
        "minutes_pending_approval": pending_approval,
    }
