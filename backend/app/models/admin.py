"""Admin dashboard data models.

Privacy boundary: These models define exactly what the admin API serializes.
Private fields (pronouns, overwhelm_triggers, never_do, anything_to_remember,
memory contents, conversation history, .env values) are NEVER included.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    RUNNING = "running"
    STARTING = "starting"
    DEGRADED = "degraded"
    STOPPED = "stopped"


class AgentHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


class MemoryCount(BaseModel):
    short: int = 0
    long: int = 0


class ConfigSummary(BaseModel):
    """Non-private config fields only.

    These fields are safe to display in the admin dashboard.
    NEVER add: pronouns, overwhelm_triggers, never_do, anything_to_remember,
    memory contents, or secrets.
    """

    energy_peak: Optional[str] = None
    information_format: Optional[str] = None
    morning_checkin: Optional[str] = None
    evening_checkin: Optional[str] = None
    agent_name: Optional[str] = None
    personality: Optional[str] = None


class AgentInfo(BaseModel):
    agent_id: str
    display_name: str
    owner_name: str
    role: str
    status: AgentStatus
    health: AgentHealth
    last_active: Optional[datetime] = None
    uptime_since: Optional[datetime] = None
    memory_count: MemoryCount = Field(default_factory=MemoryCount)
    interactions_today: int = 0
    config_summary: ConfigSummary = Field(default_factory=ConfigSummary)


class PlaneResponse(BaseModel):
    plane_name: str
    last_updated: datetime
    agents: list[AgentInfo]


class LogLine(BaseModel):
    timestamp: str
    message: str


class LogResponse(BaseModel):
    agent_id: str
    lines: list[LogLine]


class RestartResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    health: AgentHealth
    message: str


class RemoveRequest(BaseModel):
    confirm: bool
    agent_id: str


class RemoveResponse(BaseModel):
    agent_id: str
    removed: bool
    message: str


class ErrorResponse(BaseModel):
    detail: str
