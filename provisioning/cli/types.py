"""
Pydantic models for agent configuration file frontmatter validation.

Each model corresponds to one of the 6 per-agent config files:
  SOUL.md, USER.md, IDENTITY.md, AGENTS.md, HEARTBEAT.md, MEMORY.md

Validators enforce:
  - agent_id must be slug-case (lowercase letters, digits, hyphens)
  - morning/evening_checkin_time must be valid HH:MM (24h)
  - encrypt_at_rest must be True
  - sensitive_categories must include all 5 required categories

Schema evolution
----------------
Add new optional fields freely. Removing or renaming required fields
requires a version bump in the `version` field and a migration note in
agents/schema/CHANGELOG.md.  Validators are version-agnostic unless a
field meaning changes incompatibly.
"""

from __future__ import annotations

import re
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
HHMM_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

REQUIRED_SENSITIVE_CATEGORIES = frozenset(
    {
        "member_data",
        "grievance_details",
        "negotiation_strategy",
        "financial_account_info",
        "executive_session_content",
    }
)

# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------


def _validate_agent_id(value: str) -> str:
    """Enforce slug-case: lowercase, hyphens, no spaces, no leading/trailing hyphens."""
    if not SLUG_PATTERN.match(value):
        raise ValueError(
            f"agent_id must be slug-case (lowercase letters, digits, hyphens; "
            f"must start with a letter and not end with a hyphen). Got: {value!r}"
        )
    return value


def _validate_hhmm(value: str, field_name: str) -> str:
    """Enforce HH:MM 24-hour time format."""
    if not HHMM_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must be a valid 24-hour time in HH:MM format "
            f"(e.g. '09:00', '17:30'). Got: {value!r}"
        )
    return value


# ---------------------------------------------------------------------------
# Base model — strict mode prevents silent type coercion across all subclasses
# ---------------------------------------------------------------------------


class AgentConfigBase(BaseModel):
    model_config = ConfigDict(strict=True)

    version: str
    agent_id: str

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return _validate_agent_id(v)


# ---------------------------------------------------------------------------
# SOUL.md
# ---------------------------------------------------------------------------


class SoulConfig(AgentConfigBase):
    """Core personality, values, and communication style of the agent."""

    personality_traits: list[str]
    communication_style: str
    values: list[str]
    bad_news_approach: str


# ---------------------------------------------------------------------------
# USER.md
# ---------------------------------------------------------------------------


class UserConfig(AgentConfigBase):
    """The human this agent serves — preferences, context, working style."""

    owner_name: str
    owner_role: str
    pronouns: str
    energy_pattern: Literal["morning", "mid-morning", "afternoon", "evening", "variable"]
    focus_style: Literal["deep_blocks", "pomodoro", "flow_based"]
    overwhelm_triggers: list[str]
    information_format: Literal["bullets", "prose", "tables", "mixed"]
    current_time_sinks: list[str]


# ---------------------------------------------------------------------------
# IDENTITY.md
# ---------------------------------------------------------------------------


class IdentityConfig(AgentConfigBase):
    """Agent's name, avatar persona, and role definition."""

    agent_name: Union[str, Literal["self_selected"]]
    avatar_description: str
    role_definition: str
    organization: str


# ---------------------------------------------------------------------------
# AGENTS.md
# ---------------------------------------------------------------------------


class AgentsConfig(AgentConfigBase):
    """How this agent collaborates with others in the agents plane."""

    plane_name: str
    collaborates_with: list[str]
    escalation_path: str
    shared_tools: list[str]

    @field_validator("collaborates_with", mode="before")
    @classmethod
    def validate_collaborates_with(cls, values: list[str]) -> list[str]:
        for v in values:
            _validate_agent_id(v)
        return values


# ---------------------------------------------------------------------------
# HEARTBEAT.md
# ---------------------------------------------------------------------------


class HeartbeatConfig(AgentConfigBase):
    """Proactive check-in schedule, reflection triggers, energy awareness."""

    morning_checkin_time: str
    evening_checkin_time: str
    reflection_triggers: list[str]
    snooze_limit: int
    energy_aware: bool

    @field_validator("morning_checkin_time")
    @classmethod
    def validate_morning_time(cls, v: str) -> str:
        return _validate_hhmm(v, "morning_checkin_time")

    @field_validator("evening_checkin_time")
    @classmethod
    def validate_evening_time(cls, v: str) -> str:
        return _validate_hhmm(v, "evening_checkin_time")


# ---------------------------------------------------------------------------
# MEMORY.md
# ---------------------------------------------------------------------------


class MemoryConfig(AgentConfigBase):
    """Long-term memory schema — what to remember, what to encrypt, what to forget."""

    retention_days_short: int
    retention_days_long: int
    encrypt_at_rest: bool
    sensitive_categories: list[str]
    forget_on_request: bool

    @field_validator("encrypt_at_rest")
    @classmethod
    def validate_encrypt_at_rest(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "encrypt_at_rest must be True. "
                "Agent memory contains sensitive union data and must always be encrypted."
            )
        return v

    @model_validator(mode="after")
    def validate_sensitive_categories(self) -> "MemoryConfig":
        present = frozenset(self.sensitive_categories)
        missing = REQUIRED_SENSITIVE_CATEGORIES - present
        if missing:
            missing_sorted = sorted(missing)
            raise ValueError(
                f"sensitive_categories is missing required categories: "
                f"{missing_sorted}. "
                f"All 5 must be present: {sorted(REQUIRED_SENSITIVE_CATEGORIES)}"
            )
        return self


# ---------------------------------------------------------------------------
# Union type for generic loading
# ---------------------------------------------------------------------------

AgentConfig = Union[
    SoulConfig,
    UserConfig,
    IdentityConfig,
    AgentsConfig,
    HeartbeatConfig,
    MemoryConfig,
]

# ---------------------------------------------------------------------------
# Legacy aliases — maps filename → model class (used by load_config.py)
# ---------------------------------------------------------------------------

FRONTMATTER_MODELS: dict[str, type[AgentConfigBase]] = {
    "SOUL.md": SoulConfig,
    "USER.md": UserConfig,
    "IDENTITY.md": IdentityConfig,
    "AGENTS.md": AgentsConfig,
    "HEARTBEAT.md": HeartbeatConfig,
    "MEMORY.md": MemoryConfig,
}

REQUIRED_CONFIG_FILES: list[str] = list(FRONTMATTER_MODELS.keys())
