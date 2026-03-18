"""
Pulse FastAPI application — main entry point.

The AIRouter is initialized at startup and stored on app.state so every
route handler can access it via request.app.state.ai_router.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from integrations.ai.router import AIRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the Pulse app."""
    # --- Startup ---
    logger.info("Initializing AI router …")
    ai_router = AIRouter()
    app.state.ai_router = ai_router

    health = await ai_router.health()
    for model, status in health.items():
        logger.info("  %s: %s", model, status)

    yield

    # --- Shutdown ---
    logger.info("Pulse shutting down.")


app = FastAPI(
    title="Pulse",
    description="AIOS/Pulse — organizational AI backend for CHCA District 1199NE",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Route imports -----------------------------------------------------------
from api.v1.ai_routes import router as ai_api_router  # noqa: E402
from api.v1.capture import router as capture_router    # noqa: E402

app.include_router(ai_api_router)
app.include_router(capture_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
