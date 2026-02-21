#!/usr/bin/env python3
"""Load and validate agent configuration files at container startup.

Reads all 6 markdown config files from /app/config/, parses their YAML
frontmatter and markdown body, and injects them into OpenClaw's system
prompt context via the OPENCLAW_SYSTEM_PROMPT environment variable.

File contents are never logged — only filenames and load status.
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("load_config")

CONFIG_DIR = "/app/config"
REQUIRED_FILES = [
    "SOUL.md",
    "USER.md",
    "IDENTITY.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "MEMORY.md",
]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and markdown body from a config file.

    Returns (frontmatter_dict, body_str). If no frontmatter is present,
    returns (empty dict, full content).
    """
    # Lazy import — only needed at startup
    import yaml

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


def load_configs() -> str:
    """Load all required config files and build the system prompt context.

    Returns the combined system prompt string. Exits with error if any
    required file is missing.
    """
    agent_id = os.environ.get("AGENT_ID", "unknown")
    missing = []
    prompt_sections = []

    for filename in REQUIRED_FILES:
        filepath = os.path.join(CONFIG_DIR, filename)
        if not os.path.isfile(filepath):
            missing.append(filename)
            logger.error("Required config file missing: %s", filename)
            continue

        with open(filepath) as f:
            content = f.read()

        frontmatter, body = parse_frontmatter(content)

        # Build a section header from the filename
        section_name = filename.replace(".md", "")
        prompt_sections.append(f"## {section_name}\n\n{body}")

        logger.info("Loaded config: %s (agent=%s)", filename, agent_id)

    if missing:
        logger.error(
            "Agent %s is missing %d required config file(s): %s",
            agent_id,
            len(missing),
            ", ".join(missing),
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
