"""Parse and validate agent config directories."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from provisioning.cli.types import (
    REQUIRED_CONFIG_FILES,
    FRONTMATTER_MODELS,
)


def parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Expects files to start with '---' and have a closing '---'.
    Returns the parsed YAML dict, or None if no frontmatter found.
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    text = text.strip()
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    yaml_block = text[3:end].strip()
    if not yaml_block:
        return None

    try:
        return yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None


def validate_config_dir(config_path: str) -> tuple[bool, list[str], dict | None]:
    """Validate an agent config directory.

    Returns:
        (is_valid, errors, identity_info)
        identity_info is a dict with agent_id, owner_name, owner_role on success.
    """
    errors: list[str] = []
    config_dir = Path(config_path)

    if not config_dir.is_dir():
        return False, [f"Config directory not found: {config_path}"], None

    # Check all 6 files exist
    missing = []
    for fname in REQUIRED_CONFIG_FILES:
        if not (config_dir / fname).is_file():
            missing.append(fname)
    if missing:
        errors.append(f"Missing files: {', '.join(missing)}")

    # Parse and validate frontmatter for each existing file
    agent_ids: set[str] = set()
    identity_info = None

    for fname in REQUIRED_CONFIG_FILES:
        fpath = config_dir / fname
        if not fpath.is_file():
            continue

        frontmatter = parse_frontmatter(fpath)
        if frontmatter is None:
            errors.append(f"{fname}: no valid YAML frontmatter found")
            continue

        model_cls = FRONTMATTER_MODELS.get(fname)
        if model_cls is None:
            continue

        try:
            validated = model_cls(**frontmatter)
            agent_ids.add(validated.agent_id)
            if fname == "IDENTITY.md":
                identity_info = {
                    "agent_id": validated.agent_id,
                    "owner_name": validated.owner_name,
                    "owner_role": validated.owner_role,
                    "agent_name": validated.agent_name,
                }
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"{fname}: {field} \u2014 {err['msg']}")

    # Check all agent_ids match
    if len(agent_ids) > 1:
        errors.append(
            f"Mismatched agent_id values across files: {', '.join(sorted(agent_ids))}"
        )
    elif len(agent_ids) == 0 and not missing:
        errors.append("No agent_id found in any config file")

    is_valid = len(errors) == 0
    return is_valid, errors, identity_info


def load_identity(config_path: str) -> dict | None:
    """Load IDENTITY.md frontmatter from a config directory."""
    identity_file = Path(config_path) / "IDENTITY.md"
    if not identity_file.is_file():
        return None
    return parse_frontmatter(identity_file)


def get_non_private_config(config_path: str) -> dict | None:
    """Load non-private config summary for display.

    Shows: owner name/role, agent name, personality, energy peak,
           format preference, check-in times, collaborates_with,
           memory retention settings.

    NEVER shows: pronouns, overwhelm_triggers, never_do,
                 memory contents, .env values.
    """
    config_dir = Path(config_path)
    if not config_dir.is_dir():
        return None

    result = {}

    # IDENTITY.md — public fields
    identity = parse_frontmatter(config_dir / "IDENTITY.md")
    if identity:
        result["agent_id"] = identity.get("agent_id")
        result["agent_name"] = identity.get("agent_name")
        result["owner_name"] = identity.get("owner_name")
        result["owner_role"] = identity.get("owner_role")
        result["persona"] = identity.get("persona")

    # SOUL.md — personality and tone only
    soul = parse_frontmatter(config_dir / "SOUL.md")
    if soul:
        result["personality"] = soul.get("personality")
        result["tone"] = soul.get("tone")

    # USER.md — energy peak and format preference only (NOT pronouns, NOT overwhelm_triggers)
    user = parse_frontmatter(config_dir / "USER.md")
    if user:
        result["energy_peak"] = user.get("energy_peak")
        result["format_preference"] = user.get("format_preference")

    # AGENTS.md — collaboration info
    agents = parse_frontmatter(config_dir / "AGENTS.md")
    if agents:
        result["collaborates_with"] = agents.get("collaborates_with")
        result["role_in_plane"] = agents.get("role_in_plane")

    # HEARTBEAT.md — check-in times
    heartbeat = parse_frontmatter(config_dir / "HEARTBEAT.md")
    if heartbeat:
        result["check_in_times"] = heartbeat.get("check_in_times")

    # MEMORY.md — retention settings only (NOT contents)
    memory = parse_frontmatter(config_dir / "MEMORY.md")
    if memory:
        result["retention_days"] = memory.get("retention_days")
        result["sensitive_categories"] = memory.get("sensitive_categories")

    return result
