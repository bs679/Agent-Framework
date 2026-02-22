"""Pydantic models for agent configuration validation."""

from pydantic import BaseModel, field_validator


REQUIRED_CONFIG_FILES = [
    "SOUL.md",
    "USER.md",
    "IDENTITY.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "MEMORY.md",
]

REQUIRED_SENSITIVE_CATEGORIES = [
    "grievance_details",
    "negotiation_strategy",
    "member_personal_info",
    "financial_records",
    "legal_communications",
]


class IdentityFrontmatter(BaseModel):
    agent_id: str
    agent_name: str
    owner_name: str
    owner_role: str
    persona: str | None = None


class SoulFrontmatter(BaseModel):
    agent_id: str
    personality: str | None = None
    tone: str | None = None
    values: list[str] | None = None


class UserFrontmatter(BaseModel):
    agent_id: str
    owner_name: str
    owner_role: str
    pronouns: str | None = None
    energy_peak: str | None = None
    format_preference: str | None = None
    overwhelm_triggers: list[str] | None = None


class AgentsFrontmatter(BaseModel):
    agent_id: str
    collaborates_with: list[str] | None = None
    role_in_plane: str | None = None


class HeartbeatFrontmatter(BaseModel):
    agent_id: str
    check_in_times: list[str] | None = None
    reflection_triggers: list[str] | None = None


class MemoryFrontmatter(BaseModel):
    agent_id: str
    retention_days: int | None = None
    sensitive_categories: list[str] | None = None
    never_forget: list[str] | None = None
    auto_forget: list[str] | None = None

    @field_validator("sensitive_categories")
    @classmethod
    def validate_sensitive_categories(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            missing = [c for c in REQUIRED_SENSITIVE_CATEGORIES if c not in v]
            if missing:
                raise ValueError(
                    f"Missing required sensitive categories: {', '.join(missing)}"
                )
        return v


FRONTMATTER_MODELS: dict[str, type[BaseModel]] = {
    "IDENTITY.md": IdentityFrontmatter,
    "SOUL.md": SoulFrontmatter,
    "USER.md": UserFrontmatter,
    "AGENTS.md": AgentsFrontmatter,
    "HEARTBEAT.md": HeartbeatFrontmatter,
    "MEMORY.md": MemoryFrontmatter,
}


class PlaneConfig(BaseModel):
    name: str
    created_at: str
    agents: list[dict] = []
    docker_network: str


class AgentEntry(BaseModel):
    agent_id: str
    owner_name: str
    owner_role: str
    container_name: str
    config_path: str
