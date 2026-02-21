"""Pulse FastAPI application — admin dashboard endpoints.

This is the admin extension to the Pulse app backend.
Mount these routes in the main Pulse app, or run standalone for development.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.admin import router as admin_router

app = FastAPI(
    title="Pulse Admin API",
    description="Admin dashboard API for CHCA Agents Plane",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
