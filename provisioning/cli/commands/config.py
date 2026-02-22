"""`aios config` subcommands — validate and inspect agent configs."""

from __future__ import annotations

from pathlib import Path

import typer

from provisioning.cli.config_loader import (
    validate_config_dir,
    get_non_private_config,
)
from provisioning.cli.output import (
    console,
    success,
    error,
    info,
)
from provisioning.cli.types import REQUIRED_CONFIG_FILES

app = typer.Typer(help="Validate and inspect agent configuration")

AGENTS_DIR = Path("agents")


@app.command("validate")
def validate(
    path: str = typer.Option(..., help="Path to agent config directory"),
) -> None:
    """Validate an agent config directory (6 files, frontmatter, Pydantic)."""
    is_valid, errors_list, identity_info = validate_config_dir(path)

    if is_valid:
        console.print()
        success("Config valid")
        info(f"Agent ID: {identity_info['agent_id']}")
        info(f"Owner: {identity_info['owner_name']}, {identity_info['owner_role']}")
        info("Files:")
        for fname in REQUIRED_CONFIG_FILES:
            info(f"  {fname}")
        console.print()
    else:
        console.print()
        error("Config has issues:")
        for e in errors_list:
            info(f"  {e}")
        console.print()
        raise typer.Exit(1)


@app.command("show")
def show(
    agent: str = typer.Option(..., help="Agent ID to show config for"),
) -> None:
    """Display non-private config summary for an agent.

    Shows owner, agent name, personality, schedule, collaborators.
    Never shows pronouns, overwhelm triggers, never_do, memory contents, or .env values.
    """
    config_path = AGENTS_DIR / agent / "config"

    if not config_path.is_dir():
        error(f"No config found for agent '{agent}' at {config_path}")
        raise typer.Exit(1)

    config = get_non_private_config(str(config_path))
    if config is None:
        error(f"Couldn't read config for agent '{agent}'")
        raise typer.Exit(1)

    console.print(f"\n[bold]Agent Config Summary:[/bold] {agent}\n")

    _show_field("Agent Name", config.get("agent_name"))
    _show_field("Owner", _format_owner(config))
    _show_field("Persona", config.get("persona"))
    _show_field("Personality", config.get("personality"))
    _show_field("Tone", config.get("tone"))
    _show_field("Energy Peak", config.get("energy_peak"))
    _show_field("Format Preference", config.get("format_preference"))
    _show_field("Check-in Times", _format_list(config.get("check_in_times")))
    _show_field("Collaborates With", _format_list(config.get("collaborates_with")))
    _show_field("Role in Plane", config.get("role_in_plane"))
    _show_field("Memory Retention", _format_retention(config.get("retention_days")))

    console.print()


def _show_field(label: str, value: str | None) -> None:
    if value:
        console.print(f"  [bold]{label}:[/bold] {value}")


def _format_owner(config: dict) -> str | None:
    name = config.get("owner_name")
    role = config.get("owner_role")
    if name and role:
        return f"{name}, {role}"
    return name


def _format_list(items: list | None) -> str | None:
    if not items:
        return None
    return ", ".join(str(i) for i in items)


def _format_retention(days: int | None) -> str | None:
    if days is None:
        return None
    return f"{days} days"
