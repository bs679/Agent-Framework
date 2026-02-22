"""
POST /api/v1/agents/capture — Quick capture endpoint (Phase 7).

Accepts a free-form note and classifies it via the AI router using the
"quick_capture" task type (sensitive=true, always local).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class CaptureRequest(BaseModel):
    text: str
    agent_id: str | None = None


class CaptureResponse(BaseModel):
    classification: str
    model_used: str
    routed_to: str
    fallback_used: bool


@router.post("/capture", response_model=CaptureResponse)
async def capture_note(body: CaptureRequest, request: Request):
    """
    Quick-capture: classify a free-form note.

    Routed through AIRouter as task "quick_capture" — sensitive by default,
    always processed locally via Ollama.
    """
    ai_router = request.app.state.ai_router

    prompt = (
        "Classify the following captured note into one of these categories: "
        "grievance, meeting, legislative, finance, correspondence, task, other.\n\n"
        "Respond with ONLY the category name, nothing else.\n\n"
        f"Note: {body.text}"
    )

    response = await ai_router.complete(task="quick_capture", prompt=prompt)

    return CaptureResponse(
        classification=response.text.strip().lower(),
        model_used=response.model_used,
        routed_to=response.routed_to,
        fallback_used=response.fallback_used,
    )
