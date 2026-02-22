"""Module 3 — Legislative Intelligence endpoints.

All endpoints require a valid Azure AD JWT.

Routes:
  GET    /api/v1/legislative              — List, filter by relevance / upcoming hearing
  POST   /api/v1/legislative              — Create (used by n8n Workflow 3)
  GET    /api/v1/legislative/{id}         — Detail
  PATCH  /api/v1/legislative/{id}         — Update action_items, status
  POST   /api/v1/legislative/{id}/testimony-draft — AI-drafted testimony (Kimi K2)

AI routing note:
  testimony_draft routes to Kimi K2 if enabled (public content, quality matters).
  Falls back to Ollama if Kimi K2 is unavailable. See config/ai-routing.yaml.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from integrations.pulse.core.auth import get_current_user
from integrations.pulse.db.models.legislative import LegislativeItem
from integrations.pulse.db.session import get_db

router = APIRouter(prefix="/api/v1/legislative", tags=["legislative"])

VALID_RELEVANCE = {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LegislativeItemCreate(BaseModel):
    bill_number: str = Field(..., max_length=30)
    title: str = Field(..., max_length=300)
    committee: Optional[str] = Field(None, max_length=150)
    hearing_date: Optional[date] = None
    relevance: str = "medium"
    status: str = "active"
    summary: Optional[str] = None
    action_items: Optional[str] = None


class LegislativeItemPatch(BaseModel):
    committee: Optional[str] = None
    hearing_date: Optional[date] = None
    relevance: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[str] = None


class LegislativeItemOut(BaseModel):
    id: int
    bill_number: str
    title: str
    committee: Optional[str]
    hearing_date: Optional[date]
    relevance: str
    status: str
    summary: Optional[str]
    action_items: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestimonyDraftResponse(BaseModel):
    bill_number: str
    bill_title: str
    draft: str
    model_used: str
    routed_to: str
    note: str = "Review and edit before use. This draft is never auto-submitted."


# ---------------------------------------------------------------------------
# GET /api/v1/legislative
# ---------------------------------------------------------------------------

@router.get("", response_model=list[LegislativeItemOut])
def list_legislative(
    relevance: Optional[str] = Query(None, description="Filter by relevance: high | medium | low"),
    upcoming_hearing: bool = Query(
        False,
        description="If true, only show items with a hearing_date >= today",
    ),
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LegislativeItemOut]:
    """List legislative items with optional filters."""
    q = db.query(LegislativeItem)

    if relevance:
        if relevance not in VALID_RELEVANCE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"relevance must be one of: {sorted(VALID_RELEVANCE)}",
            )
        q = q.filter(LegislativeItem.relevance == relevance)

    if upcoming_hearing:
        today = date.today()
        q = q.filter(
            LegislativeItem.hearing_date.isnot(None),
            LegislativeItem.hearing_date >= today,
        )

    items = q.order_by(LegislativeItem.hearing_date.asc().nullslast()).all()
    return [LegislativeItemOut.model_validate(i) for i in items]


# ---------------------------------------------------------------------------
# POST /api/v1/legislative
# ---------------------------------------------------------------------------

@router.post("", response_model=LegislativeItemOut, status_code=status.HTTP_201_CREATED)
def create_legislative(
    body: LegislativeItemCreate,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegislativeItemOut:
    """Create a new legislative item. Typically called by n8n Workflow 3."""
    if body.relevance not in VALID_RELEVANCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"relevance must be one of: {sorted(VALID_RELEVANCE)}",
        )

    item = LegislativeItem(
        bill_number=body.bill_number,
        title=body.title,
        committee=body.committee,
        hearing_date=body.hearing_date,
        relevance=body.relevance,
        status=body.status,
        summary=body.summary,
        action_items=body.action_items,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return LegislativeItemOut.model_validate(item)


# ---------------------------------------------------------------------------
# GET /api/v1/legislative/{id}
# ---------------------------------------------------------------------------

@router.get("/{item_id}", response_model=LegislativeItemOut)
def get_legislative(
    item_id: int,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegislativeItemOut:
    """Return full detail for a single legislative item."""
    item = db.query(LegislativeItem).filter(LegislativeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Legislative item not found")
    return LegislativeItemOut.model_validate(item)


# ---------------------------------------------------------------------------
# PATCH /api/v1/legislative/{id}
# ---------------------------------------------------------------------------

@router.patch("/{item_id}", response_model=LegislativeItemOut)
def update_legislative(
    item_id: int,
    body: LegislativeItemPatch,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegislativeItemOut:
    """Update action_items, status, or other fields on a legislative item."""
    item = db.query(LegislativeItem).filter(LegislativeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Legislative item not found")

    if body.relevance is not None and body.relevance not in VALID_RELEVANCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"relevance must be one of: {sorted(VALID_RELEVANCE)}",
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)

    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return LegislativeItemOut.model_validate(item)


# ---------------------------------------------------------------------------
# POST /api/v1/legislative/{id}/testimony-draft
# ---------------------------------------------------------------------------

@router.post("/{item_id}/testimony-draft", response_model=TestimonyDraftResponse)
async def testimony_draft(
    item_id: int,
    request: Request,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestimonyDraftResponse:
    """Draft union testimony for a CT General Assembly hearing.

    Routes to Kimi K2 (public content, quality critical). Falls back to
    Ollama if Kimi K2 is disabled. Never auto-submits anything.
    """
    item = db.query(LegislativeItem).filter(LegislativeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Legislative item not found")

    ai_router = request.app.state.ai_router

    prompt = (
        f"Draft union testimony for a CT General Assembly hearing on: {item.title}. "
        "Speaker is the president of a healthcare workers union (Connecticut Health Care "
        "Associates, District 1199NE, AFSCME), representing workers at Bradley Memorial, "
        "Norwalk, and Waterbury hospitals and school districts in CT Regions 12, 13, and 17. "
        "Tone: professional, direct, grounded in worker experience. Keep under 500 words. "
        "Begin with 'Good [morning/afternoon], [Chair] and members of the committee.' "
        "Include a clear ask at the end."
    )
    if item.summary:
        prompt += f"\n\nBill summary: {item.summary}"
    if item.action_items:
        prompt += f"\n\nKey union concerns: {item.action_items}"

    response = await ai_router.complete(task="testimony_draft", prompt=prompt)

    return TestimonyDraftResponse(
        bill_number=item.bill_number,
        bill_title=item.title,
        draft=response.text,
        model_used=response.model_used,
        routed_to=response.routed_to,
    )
