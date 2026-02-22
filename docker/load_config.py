#!/usr/bin/env python3
"""Load and validate agent configuration files at container startup.

Reads all 6 markdown config files from /app/config/, parses their YAML
frontmatter and markdown body, validates frontmatter against the Pydantic
schema models, and injects the combined context into OpenClaw via the
OPENCLAW_SYSTEM_PROMPT environment variable.

File contents are never logged — only filenames and load status.
"""

import os
import sys
import logging

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("load_config")

CONFIG_DIR = "/app/config"

# Map from filename to the Pydantic model that validates its frontmatter.
# Imported lazily to avoid pulling the full provisioning package at import time
# if it isn't installed inside the container.
_SCHEMA_MAP: dict[str, str] = {
    "SOUL.md": "SoulConfig",
    "USER.md": "UserConfig",
    "IDENTITY.md": "IdentityConfig",
    "AGENTS.md": "AgentsConfig",
    "HEARTBEAT.md": "HeartbeatConfig",
    "MEMORY.md": "MemoryConfig",
}

REQUIRED_FILES = list(_SCHEMA_MAP.keys())


def _get_validator(model_name: str):
    """Return the Pydantic model class or None if provisioning pkg unavailable."""
    try:
        import importlib
        mod = importlib.import_module("provisioning.cli.types")
        return getattr(mod, model_name, None)
    except ImportError:
        return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and markdown body from a config file.

    Returns (frontmatter_dict, body_str). If no frontmatter is present,
    returns (empty dict, full content).
    """
    if not content.startswith("---"):
        return {}, content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content.strip()

    frontmatter_raw = parts[1].strip()
    body = parts[2].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse YAML frontmatter: %s", exc)
        frontmatter = {}

    return frontmatter, body


def validate_frontmatter(filename: str, frontmatter: dict, agent_id: str) -> bool:
    """Validate frontmatter against the registered Pydantic model.

    Returns True if valid (or if schema unavailable). Logs errors and
    returns False on validation failure — caller decides whether to abort.
    """
    model_name = _SCHEMA_MAP.get(filename)
    if not model_name:
        return True

    validator = _get_validator(model_name)
    if validator is None:
        logger.debug(
            "Schema validation skipped for %s — provisioning package not installed",
            filename,
        )
        return True

    try:
        validator.model_validate(frontmatter)
        logger.info("Schema valid: %s (agent=%s)", filename, agent_id)
        return True
    except Exception as exc:  # pydantic.ValidationError
        # Log field-level errors without logging values (values may be sensitive)
        field_errors = []
        if hasattr(exc, "errors"):
            field_errors = [
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors()
            ]
        logger.error(
            "Schema validation failed for %s (agent=%s): %s",
            filename,
            agent_id,
            "; ".join(field_errors) or str(exc),
        )
        return False


def load_configs() -> str:
    """Load and validate all required config files, build the system prompt.

    Returns the combined system prompt string. Exits with code 1 if any
    required file is missing or fails schema validation.
    """
    agent_id = os.environ.get("AGENT_ID", "unknown")
    errors: list[str] = []
    prompt_sections = []

    for filename in REQUIRED_FILES:
        filepath = os.path.join(CONFIG_DIR, filename)
        if not os.path.isfile(filepath):
            errors.append(f"{filename}: file missing")
            logger.error("Required config file missing: %s", filename)
            continue

        with open(filepath) as f:
            content = f.read()

        frontmatter, body = parse_frontmatter(content)

        if not validate_frontmatter(filename, frontmatter, agent_id):
            errors.append(f"{filename}: schema validation failed")
            # Continue loading other files so all errors are surfaced at once

        section_name = filename.replace(".md", "")
        prompt_sections.append(f"## {section_name}\n\n{body}")

        logger.info("Loaded config: %s (agent=%s)", filename, agent_id)

    if errors:
        logger.error(
            "Agent %s failed to load: %d error(s): %s",
            agent_id,
            len(errors),
            "; ".join(errors),
        )
        sys.exit(1)

    logger.info("All %d config files loaded for agent %s", len(REQUIRED_FILES), agent_id)
    return "\n\n---\n\n".join(prompt_sections)


def inject_config(system_prompt: str) -> None:
    """Inject the combined config into OpenClaw's system prompt mechanism.

    OpenClaw reads system prompt context from the OPENCLAW_SYSTEM_PROMPT
    environment variable. We also write to /app/config/system_prompt.txt
    as a fallback for config-file-based loading.
    """
    # Set environment variable for OpenClaw
    os.environ["OPENCLAW_SYSTEM_PROMPT"] = system_prompt

    # Also write to a file that OpenClaw can pick up
    prompt_path = os.path.join(CONFIG_DIR, "system_prompt.txt")
    # Config dir is read-only in production; write to a writable location
    writable_prompt_path = "/app/system_prompt.txt"
    with open(writable_prompt_path, "w") as f:
        f.write(system_prompt)

    logger.info("System prompt written to %s", writable_prompt_path)


def main():
    agent_id = os.environ.get("AGENT_ID", "unknown")
    plane_name = os.environ.get("PLANE_NAME", "unknown")

    logger.info("Loading configuration for agent=%s plane=%s", agent_id, plane_name)

    system_prompt = load_configs()
    inject_config(system_prompt)

    logger.info("Configuration loaded successfully for agent=%s", agent_id)


if __name__ == "__main__":
    main()
