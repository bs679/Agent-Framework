"""aios agents — subcommands for managing individual agents."""

import os
import secrets
import sys
from pathlib import Path

import click

from provisioning.cli.registry import add_agent_to_plane, get_plane, list_agents

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@click.group()
def agents():
    """Manage individual agents within a plane."""
    pass


@agents.command()
@click.option("--plane", required=True, help="Plane to add the agent to")
@click.option("--name", required=True, help="Agent identifier (lowercase, no spaces)")
@click.option("--owner", required=True, help="Owner email address")
@click.option("--role", default="standard", help="Agent role (default: standard)")
def add(plane, name, owner, role):
    """Register a new agent in a plane and generate its .env file."""
    # Validate agent name
    agent_id = name.lower().replace(" ", "-")
    if agent_id != name:
        click.echo(f"Note: agent ID normalized to '{agent_id}'")

    # Register in the plane
    try:
        agent = add_agent_to_plane(plane, agent_id, owner, role)
    except (KeyError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Create agent directories
    agent_dir = PROJECT_ROOT / "agents" / agent_id
    config_dir = agent_dir / "config"
    memory_dir = agent_dir / "memory"
    config_dir.mkdir(parents=True, exist_ok=True)
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Generate .env file (refuse to overwrite existing)
    env_path = agent_dir / ".env"
    _generate_env(env_path, agent_id, owner, plane)

    click.echo(f"Agent '{agent_id}' added to plane '{plane}'")
    click.echo(f"  Owner: {owner}")
    click.echo(f"  Role: {role}")
    click.echo(f"  Config dir: {config_dir}")
    click.echo(f"  Memory dir: {memory_dir}")
    click.echo(f"  Env file: {env_path}")


@agents.command("list")
@click.option("--plane", required=True, help="Plane to list agents from")
def list_cmd(plane):
    """List all agents in a plane."""
    try:
        agents_dict = list_agents(plane)
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not agents_dict:
        click.echo(f"No agents in plane '{plane}'.")
        return

    click.echo(f"Agents in plane '{plane}':")
    for agent_id, agent in agents_dict.items():
        click.echo(f"  {agent_id} (owner={agent['owner']}, role={agent['role']})")


def _generate_env(env_path: Path, agent_id: str, owner: str, plane_name: str) -> None:
    """Generate a .env file for an agent.

    IMPORTANT: Refuses to overwrite an existing .env file to prevent
    accidental rotation of MEMORY_ENCRYPTION_KEY, which would make
    existing encrypted memory unreadable.
    """
    if env_path.exists():
        click.echo(f"  .env already exists at {env_path} — skipping generation")
        click.echo("  (To regenerate, manually delete the file first. This protects your encryption key.)")
        return

    encryption_key = secrets.token_hex(32)

    env_content = f"""AGENT_ID={agent_id}
AGENT_OWNER={owner}
PLANE_NAME={plane_name}

# AI backends
OLLAMA_HOST=host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
ANTHROPIC_API_KEY=
AI_FALLBACK_TO_API=false

# Pulse integration
PULSE_API_URL=http://host.docker.internal:8000
PULSE_API_TOKEN=

# Microsoft 365
MS_TENANT_ID=
MS_CLIENT_ID=
MS_CLIENT_SECRET=

# Memory
MEMORY_ENCRYPTION_KEY={encryption_key}
MEMORY_PATH=/app/memory
"""

    env_path.write_text(env_content)
    click.echo(f"  Generated .env with unique MEMORY_ENCRYPTION_KEY")
