"""Pulse agent plane configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class AgentPlaneSettings(BaseSettings):
    """Settings for the agent-plane <-> Pulse integration."""

    agent_plane_enabled: bool = True
    agent_plane_url: str = "http://localhost:8001"
    agent_context_cache_ttl: int = 300  # seconds
    executive_session_keywords: str = (
        "executive session,exec session,board executive"
    )
    db_auto_create_on_startup: bool = False

    # Azure AD
    azure_ad_tenant_id: str = ""
    azure_ad_client_id: str = ""
    azure_ad_audience: str = "api://pulse-app"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def executive_keywords_list(self) -> list[str]:
        """Return executive-session keywords as a lowercase list."""
        return [
            kw.strip().lower()
            for kw in self.executive_session_keywords.split(",")
            if kw.strip()
        ]


@lru_cache
def get_settings() -> AgentPlaneSettings:
    return AgentPlaneSettings()
