"""Agent service — reads agent state from the filesystem and Docker.

Privacy boundary: This service NEVER reads or returns:
  - pronouns, overwhelm_triggers, never_do, anything_to_remember
  - memory file contents or conversation history
  - .env values or secrets

Config files are parsed selectively — only safe fields are extracted.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models.admin import (
    AgentHealth,
    AgentInfo,
    AgentStatus,
    ConfigSummary,
    LogLine,
    MemoryCount,
)

AGENTS_DIR = Path(os.environ.get("AGENTS_DIR", "agents"))

# Fields that are NEVER extracted from config files
PRIVATE_FIELDS = frozenset(
    {
        "pronouns",
        "overwhelm_triggers",
        "never_do",
        "anything_to_remember",
        "memory",
        "conversation_history",
    }
)

# Patterns that indicate a log line contains secrets
SECRET_PATTERNS = re.compile(
    r"(SECRET|KEY|TOKEN|PASSWORD)", re.IGNORECASE
)


def _get_agent_dirs() -> list[Path]:
    """Return all agent directories under AGENTS_DIR."""
    if not AGENTS_DIR.exists():
        return []
    return sorted(
        [d for d in AGENTS_DIR.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )


def _parse_safe_config(agent_dir: Path) -> ConfigSummary:
    """Extract only non-private config fields from agent config files.

    Reads HEARTBEAT.md, USER.md, IDENTITY.md, SOUL.md for safe fields.
    Never reads or returns private data.
    """
    summary = ConfigSummary()

    heartbeat_path = agent_dir / "config" / "HEARTBEAT.md"
    if heartbeat_path.exists():
        content = heartbeat_path.read_text(errors="replace")
        morning = re.search(
            r"morning[_\s]*check[\s_-]*in[:\s]*(\d{1,2}:\d{2})", content, re.IGNORECASE
        )
        evening = re.search(
            r"evening[_\s]*check[\s_-]*in[:\s]*(\d{1,2}:\d{2})", content, re.IGNORECASE
        )
        if morning:
            summary.morning_checkin = morning.group(1)
        if evening:
            summary.evening_checkin = evening.group(1)

    user_path = agent_dir / "config" / "USER.md"
    if user_path.exists():
        content = user_path.read_text(errors="replace")
        energy = re.search(
            r"energy[_\s]*peak[:\s]*(morning|afternoon|evening|night)",
            content,
            re.IGNORECASE,
        )
        fmt = re.search(
            r"information[_\s]*format[:\s]*(\w[\w\s]*)",
            content,
            re.IGNORECASE,
        )
        if energy:
            summary.energy_peak = energy.group(1).lower()
        if fmt:
            summary.information_format = fmt.group(1).strip()[:30]

    identity_path = agent_dir / "config" / "IDENTITY.md"
    if identity_path.exists():
        content = identity_path.read_text(errors="replace")
        name = re.search(r"agent[_\s]*name[:\s]*(.+)", content, re.IGNORECASE)
        if name:
            summary.agent_name = name.group(1).strip()[:50]

    soul_path = agent_dir / "config" / "SOUL.md"
    if soul_path.exists():
        content = soul_path.read_text(errors="replace")
        personality = re.search(
            r"personality[:\s]*(.+)", content, re.IGNORECASE
        )
        if personality:
            summary.personality = personality.group(1).strip()[:80]

    return summary


def _count_memory_files(agent_dir: Path) -> MemoryCount:
    """Count memory items without reading their contents."""
    memory_dir = agent_dir / "memory"
    if not memory_dir.exists():
        return MemoryCount()

    short_dir = memory_dir / "short"
    long_dir = memory_dir / "long"

    short_count = len(list(short_dir.iterdir())) if short_dir.exists() else 0
    long_count = len(list(long_dir.iterdir())) if long_dir.exists() else 0

    return MemoryCount(short=short_count, long=long_count)


def _read_agent_meta(agent_dir: Path) -> dict:
    """Read agent metadata from meta.json if it exists."""
    import json

    meta_path = agent_dir / "meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _get_container_status(agent_id: str) -> tuple[AgentStatus, AgentHealth, Optional[datetime]]:
    """Check Docker container status for an agent.

    Falls back to filesystem-based status if Docker is unavailable.
    """
    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(f"openclaw-{agent_id}")
        state = container.status

        if state == "running":
            started_at = container.attrs.get("State", {}).get("StartedAt")
            uptime = None
            if started_at:
                uptime = datetime.fromisoformat(
                    started_at.replace("Z", "+00:00")
                )
            return AgentStatus.RUNNING, AgentHealth.HEALTHY, uptime
        elif state == "created" or state == "restarting":
            return AgentStatus.STARTING, AgentHealth.DEGRADED, None
        else:
            return AgentStatus.STOPPED, AgentHealth.UNREACHABLE, None
    except Exception:
        # Docker not available — use filesystem status
        return AgentStatus.STOPPED, AgentHealth.UNREACHABLE, None


def get_all_agents() -> list[AgentInfo]:
    """Return info for all agents. Never includes private data."""
    agents = []

    for agent_dir in _get_agent_dirs():
        agent_id = agent_dir.name
        meta = _read_agent_meta(agent_dir)
        status, health, uptime = _get_container_status(agent_id)
        config = _parse_safe_config(agent_dir)
        memory = _count_memory_files(agent_dir)

        agent = AgentInfo(
            agent_id=agent_id,
            display_name=meta.get("display_name", config.agent_name or agent_id),
            owner_name=meta.get("owner_name", "Unknown"),
            role=meta.get("role", "Staff"),
            status=status,
            health=health,
            last_active=meta.get("last_active"),
            uptime_since=uptime,
            memory_count=memory,
            interactions_today=meta.get("interactions_today", 0),
            config_summary=config,
        )
        agents.append(agent)

    return agents


def get_agent_logs(agent_id: str, tail: int = 50) -> list[LogLine]:
    """Return last N log lines, filtered for secrets.

    Any line containing SECRET, KEY, TOKEN, or PASSWORD is replaced
    with '[sensitive -- not shown]'.
    """
    lines: list[LogLine] = []

    # Try Docker logs first
    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(f"openclaw-{agent_id}")
        raw_logs = container.logs(tail=tail, timestamps=True).decode(
            "utf-8", errors="replace"
        )
        for line in raw_logs.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(" ", 1)
            ts = parts[0] if len(parts) > 1 else ""
            msg = parts[1] if len(parts) > 1 else parts[0]

            if SECRET_PATTERNS.search(msg):
                msg = "[sensitive \u2014 not shown]"

            lines.append(LogLine(timestamp=ts[:8], message=msg))
        return lines
    except Exception:
        pass

    # Fallback: read from log file
    log_file = AGENTS_DIR / agent_id / "logs" / "agent.log"
    if log_file.exists():
        all_lines = log_file.read_text(errors="replace").strip().split("\n")
        for line in all_lines[-tail:]:
            if not line.strip():
                continue
            parts = line.split(" ", 2)
            ts = parts[0] if parts else ""
            msg = " ".join(parts[1:]) if len(parts) > 1 else line

            if SECRET_PATTERNS.search(msg):
                msg = "[sensitive \u2014 not shown]"

            lines.append(LogLine(timestamp=ts[:8], message=msg))

    return lines


def restart_agent(agent_id: str) -> tuple[AgentStatus, AgentHealth, str]:
    """Restart an agent's Docker container."""
    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(f"openclaw-{agent_id}")
        container.restart(timeout=30)
        container.reload()

        if container.status == "running":
            return AgentStatus.RUNNING, AgentHealth.HEALTHY, "Agent restarted successfully"
        else:
            return AgentStatus.STARTING, AgentHealth.DEGRADED, "Agent restarting"
    except Exception as e:
        return AgentStatus.STOPPED, AgentHealth.UNREACHABLE, f"Restart failed: {str(e)}"


def remove_agent(agent_id: str) -> tuple[bool, str]:
    """Stop and remove an agent's Docker container.

    Does NOT delete config or memory files — only stops the container.
    """
    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(f"openclaw-{agent_id}")
        container.stop(timeout=30)
        container.remove()
        return True, "Container stopped and removed. Config and memory files preserved."
    except Exception as e:
        return False, f"Remove failed: {str(e)}"
