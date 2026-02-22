"""Module 2 — Contract Research Tools.

All endpoints require a valid Azure AD JWT.

Routes:
  GET  /api/v1/research/wage-costing    — Year 1-3 cost projection table
  GET  /api/v1/research/bls-lookup      — Proxy to BLS public API (24h cache)
  POST /api/v1/research/proposal-draft  — AI-drafted contract proposal (Ollama, sensitive)
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from integrations.pulse.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# ---------------------------------------------------------------------------
# BLS cache — simple in-process dict with TTL
# ---------------------------------------------------------------------------
_BLS_CACHE: dict[str, tuple[float, Any]] = {}  # key → (timestamp, data)
_BLS_CACHE_TTL: float = 86_400.0  # 24 hours in seconds
_BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class YearProjection(BaseModel):
    year: int
    total_annual_cost: float
    per_member_cost: float
    cumulative_increase: float
    step_increase_amount: float


class WageCostingResponse(BaseModel):
    base_wage: float
    step_increase_pct: float
    hours_per_year: int
    headcount: int
    projections: list[YearProjection]


class BLSResponse(BaseModel):
    series_id: str
    start_year: int
    end_year: int
    cached: bool
    data: list[dict[str, Any]]


class ProposalDraftRequest(BaseModel):
    proposal_type: str = Field(
        ...,
        description="wage_increase | scheduling | benefit",
    )
    context: str = Field(..., min_length=10, max_length=4000)


class ProposalDraftResponse(BaseModel):
    proposal_type: str
    draft: str
    model_used: str
    routed_to: str


# ---------------------------------------------------------------------------
# GET /api/v1/research/wage-costing
# ---------------------------------------------------------------------------

@router.get("/wage-costing", response_model=WageCostingResponse)
def wage_costing(
    base_wage: float = Query(..., gt=0, description="Current hourly base wage"),
    step_increase_pct: float = Query(..., gt=0, le=100, description="Proposed annual step increase (%)"),
    hours_per_year: int = Query(2080, gt=0, description="Annual hours per FTE (default 2080 = 40h/week)"),
    headcount: int = Query(..., gt=0, description="Number of bargaining unit members"),
    _user: dict[str, Any] = Depends(get_current_user),
) -> WageCostingResponse:
    """Project total contract cost over 3 years for a proposed wage increase.

    Returns per-member and total costs for years 1, 2, and 3, compounding
    the step increase each year.
    """
    projections: list[YearProjection] = []
    current_wage = base_wage

    for yr in range(1, 4):
        new_wage = current_wage * (1 + step_increase_pct / 100)
        increase_amount = new_wage - base_wage  # vs. base (year 0)
        annual_cost_per_member = new_wage * hours_per_year
        total_cost = annual_cost_per_member * headcount
        cumulative_increase = ((new_wage - base_wage) / base_wage) * 100

        projections.append(
            YearProjection(
                year=yr,
                total_annual_cost=round(total_cost, 2),
                per_member_cost=round(annual_cost_per_member, 2),
                cumulative_increase=round(cumulative_increase, 4),
                step_increase_amount=round(new_wage - current_wage, 4),
            )
        )
        current_wage = new_wage

    return WageCostingResponse(
        base_wage=base_wage,
        step_increase_pct=step_increase_pct,
        hours_per_year=hours_per_year,
        headcount=headcount,
        projections=projections,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/research/bls-lookup
# ---------------------------------------------------------------------------

@router.get("/bls-lookup", response_model=BLSResponse)
async def bls_lookup(
    series_id: str = Query(..., description="BLS series identifier (e.g. CES0000000001)"),
    start_year: int = Query(..., ge=1950, le=2030),
    end_year: int = Query(..., ge=1950, le=2030),
    _user: dict[str, Any] = Depends(get_current_user),
) -> BLSResponse:
    """Proxy to the BLS public data API with a 24-hour response cache.

    Uses the BLS Public Data API v2 — no registration key required for
    public series data. Results are cached in-process to avoid hammering
    the BLS API during repeated AI research sessions.
    """
    if start_year > end_year:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_year must be <= end_year",
        )

    # Cache key is stable for the same (series_id, start_year, end_year) tuple
    cache_key = hashlib.sha256(
        f"{series_id}:{start_year}:{end_year}".encode()
    ).hexdigest()

    now = time.monotonic()
    if cache_key in _BLS_CACHE:
        ts, cached_data = _BLS_CACHE[cache_key]
        if now - ts < _BLS_CACHE_TTL:
            logger.debug("[bls-lookup] Cache hit for %s %s-%s", series_id, start_year, end_year)
            return BLSResponse(
                series_id=series_id,
                start_year=start_year,
                end_year=end_year,
                cached=True,
                data=cached_data,
            )

    payload = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_BLS_API_URL, json=payload)
            resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="BLS API request timed out",
        )
    except httpx.HTTPError as exc:
        logger.error("[bls-lookup] BLS API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"BLS API returned an error: {exc}",
        )

    bls_json = resp.json()
    status_code = bls_json.get("status", "FAILED")
    if status_code != "REQUEST_SUCCEEDED":
        messages = bls_json.get("message", [])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"BLS API reported failure: {messages}",
        )

    series_list = bls_json.get("Results", {}).get("series", [])
    data_points: list[dict[str, Any]] = []
    if series_list:
        data_points = series_list[0].get("data", [])

    # Store in cache
    _BLS_CACHE[cache_key] = (now, data_points)

    return BLSResponse(
        series_id=series_id,
        start_year=start_year,
        end_year=end_year,
        cached=False,
        data=data_points,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/research/proposal-draft
# ---------------------------------------------------------------------------

@router.post("/proposal-draft", response_model=ProposalDraftResponse)
async def proposal_draft(
    body: ProposalDraftRequest,
    request: Request,
    _user: dict[str, Any] = Depends(get_current_user),
) -> ProposalDraftResponse:
    """Draft a union contract proposal using the AIRouter.

    Routes to Ollama (sensitive=true — negotiation strategy never leaves local).
    Returns draft text for Dave to review and edit. Never auto-submits.
    """
    valid_types = {"wage_increase", "scheduling", "benefit"}
    if body.proposal_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"proposal_type must be one of: {sorted(valid_types)}",
        )

    ai_router = request.app.state.ai_router

    prompt = (
        f"Draft a union contract proposal for {body.proposal_type}. "
        f"Context: {body.context}. "
        "Format as a contract article with WHEREAS clauses and numbered sections. "
        "This is for a healthcare workers union (CHCA, District 1199NE, AFSCME) "
        "representing workers at Bradley Memorial, Norwalk, and Waterbury hospitals "
        "and school districts in CT Regions 12, 13, and 17."
    )

    response = await ai_router.complete(task="contract_proposal", prompt=prompt)

    return ProposalDraftResponse(
        proposal_type=body.proposal_type,
        draft=response.text,
        model_used=response.model_used,
        routed_to=response.routed_to,
    )
