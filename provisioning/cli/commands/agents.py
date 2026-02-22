"""`aios agents` subcommands — add, list, manage individual agents."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

import typer

from provisioning.cli import docker_client as dc
from provisioning.cli.config_loader import validate_config_dir, load_identity
from provisioning.cli.output import (
    console,
    success,
    warning,
    error,
    info,
    stopped,
    print_agent_row,
    status_icon,
)

app = typer.Typer(help="Manage agents within a plane")

PLANES_DIR = Path("planes")
AGENTS_DIR = Path("agents")


def _load_plane(name: str) -> dict | None:
    path = PLANES_DIR / f"{name}.json"
    if not path.is_file():
        error(f"Plane '{name}' not found \u2014 run 'aios planes create --name {name}' first")
        return None
    return json.loads(path.read_text())


def _save_plane(name: str, data: dict) -> None:
    path = PLANES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")


def _ensure_env_file(agent_id: str) -> str:
    """Ensure agents/{id}/.env exists with at least MEMORY_ENCRYPTION_KEY."""
    agent_dir = AGENTS_DIR / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    env_path = agent_dir / ".env"

    if env_path.is_file():
        return str(env_path)

    key = secrets.token_hex(32)
    env_path.write_text(f"MEMORY_ENCRYPTION_KEY={key}\n")
    success("Generated .env with MEMORY_ENCRYPTION_KEY")
    return str(env_path)


@app.command("add")
def add(
    config: str = typer.Option(..., help="Path to agent config directory"),
    plane: str = typer.Option(..., help="Plane to add the agent to"),
) -> None:
    """Add an agent to a plane from a config directory."""
    plane_data = _load_plane(plane)
    if plane_data is None:
        raise typer.Exit(1)

    # Validate config
    is_valid, errors_list, identity_info = validate_config_dir(config)

    if not is_valid:
        error("Config validation failed:")
        for e in errors_list:
            info(f"  {e}")
        raise typer.Exit(1)

    agent_id = identity_info["agent_id"]
    owner_name = identity_info["owner_name"]
    owner_role = identity_info["owner_role"]
    container_name = f"openclaw-{agent_id}"

    console.print(f"\nAdding agent {agent_id}...")
    success("Config validated")

    # Check if already in plane
    existing_ids = [a["agent_id"] for a in plane_data.get("agents", [])]
    if agent_id in existing_ids:
        warning(f"Agent '{agent_id}' is already registered in plane '{plane}' \u2014 skipping")
        raise typer.Exit(0)

    # Connect to Docker
    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    # Ensure .env file exists
    env_file = _ensure_env_file(agent_id)

    # Ensure memory dir exists
    memory_dir = AGENTS_DIR / agent_id / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Resolve absolute paths for volumes
    config_abs = str(Path(config).resolve())
    memory_abs = str(memory_dir.resolve())

    volumes = {
        config_abs: {"bind": "/app/config", "mode": "ro"},
        memory_abs: {"bind": "/app/memory", "mode": "rw"},
    }

    environment = {
        "AGENT_ID": agent_id,
        "PLANE_NAME": plane,
        "OLLAMA_HOST": "host.docker.internal:11434",
    }

    network = plane_data.get("docker_network", f"{plane}-net")

    container = dc.create_container(
        client,
        name=container_name,
        network=network,
        volumes=volumes,
        env_file_path=env_file,
        environment=environment,
    )

    if container is None:
        raise typer.Exit(1)

    # Start container
    if dc.start_container(client, container_name):
        success("Agent started")
    else:
        error("Agent container created but failed to start")
        raise typer.Exit(1)

    # Register in plane JSON
    agent_entry = {
        "agent_id": agent_id,
        "owner_name": owner_name,
        "owner_role": owner_role,
        "container_name": container_name,
        "config_path": config,
    }
    plane_data.setdefault("agents", []).append(agent_entry)
    _save_plane(plane, plane_data)

    console.print()
    success(f"Agent '{agent_id}' added to plane '{plane}'")


@app.command("list")
def list_agents(
    plane: str = typer.Option(..., help="Plane to list agents from"),
) -> None:
    """List all agents registered in a plane."""
    plane_data = _load_plane(plane)
    if plane_data is None:
        raise typer.Exit(1)

    agents = plane_data.get("agents", [])
    if not agents:
        stopped(f"No agents in plane '{plane}'")
        return

    client = dc.get_client()

    console.print(f"\n[bold]{plane_data['name']}[/bold] ({plane_data.get('docker_network', '')})")

    for agent in agents:
        agent_id = agent.get("agent_id", "unknown")
        container_name = agent.get("container_name", f"openclaw-{agent_id}")
        description = f"{agent.get('owner_name', '')}, {agent.get('owner_role', '')}"

        if client:
            container_status = dc.get_container_status(client, container_name)
        else:
            container_status = "stopped"

        print_agent_row(agent_id, container_status, description)

    console.print()


@app.command("status")
def agent_status(
    agent: str = typer.Option(..., help="Agent ID to check status for"),
) -> None:
    """Show detailed status for a single agent."""
    container_name = f"openclaw-{agent}"

    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    details = dc.get_container_details(client, container_name)
    if details is None:
        stopped(f"Agent '{agent}' has no container (not deployed)")
        return

    icon, color = status_icon(details["status"])

    console.print(f"\n[bold]Agent:[/bold] {agent}")
    console.print(f"[bold]Status:[/bold] [{color}]{icon} {details['status']}[/{color}]")
    console.print(f"[bold]Image:[/bold] {details['image']}")
    console.print(f"[bold]Started:[/bold] {details['started_at']}")
    if details["finished_at"]:
        console.print(f"[bold]Stopped:[/bold] {details['finished_at']}")
    console.print(f"[bold]Health:[/bold] {details['health']}")
    console.print()


@app.command("logs")
def logs(
    agent: str = typer.Option(..., help="Agent ID"),
    tail: int = typer.Option(50, help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """Stream logs from an agent container (sensitive values filtered)."""
    container_name = f"openclaw-{agent}"

    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    if follow:
        # Streaming mode
        result = dc.get_container_logs(client, container_name, tail=tail, follow=True)
        if result is None:
            raise typer.Exit(1)

        sensitive_keywords = ["SECRET", "KEY", "TOKEN", "PASSWORD"]
        try:
            for chunk in result:
                line = chunk.decode("utf-8", errors="replace").rstrip()
                if any(kw in line.upper() for kw in sensitive_keywords):
                    console.print("[sensitive \u2014 not shown]")
                else:
                    console.print(line)
        except KeyboardInterrupt:
            pass
    else:
        result = dc.get_container_logs(client, container_name, tail=tail, follow=False)
        if result is None:
            raise typer.Exit(1)
        if result:
            console.print(result)
        else:
            stopped("No log output")


@app.command("restart")
def restart(
    agent: str = typer.Option(..., help="Agent ID to restart"),
) -> None:
    """Restart an agent container and report new status."""
    container_name = f"openclaw-{agent}"

    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    console.print(f"Restarting agent {agent}...")

    if not dc.restart_container(client, container_name):
        raise typer.Exit(1)

    # Check new status
    details = dc.get_container_details(client, container_name)
    if details:
        icon, color = status_icon(details["status"])
        success(f"Agent '{agent}' restarted \u2014 [{color}]{details['status']}[/{color}]")
        if details["health"] != "no health check configured":
            info(f"Health: {details['health']}")
    else:
        success(f"Agent '{agent}' restart command sent")


@app.command("remove")
def remove(
    agent: str = typer.Option(..., help="Agent ID to remove"),
) -> None:
    """Remove an agent container. Preserves config and memory data."""
    container_name = f"openclaw-{agent}"

    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    console.print(f"Removing agent {agent}...")

    if not dc.remove_container(client, container_name):
        raise typer.Exit(1)

    success(f"Container '{container_name}' removed")

    # Remove from all plane JSON files
    planes_dir = Path("planes")
    if planes_dir.is_dir():
        for pf in planes_dir.glob("*.json"):
            try:
                plane = json.loads(pf.read_text())
                original_count = len(plane.get("agents", []))
                plane["agents"] = [
                    a for a in plane.get("agents", []) if a.get("agent_id") != agent
                ]
                if len(plane["agents"]) < original_count:
                    pf.write_text(json.dumps(plane, indent=2) + "\n")
                    success(f"Removed from plane '{plane['name']}'")
            except (json.JSONDecodeError, OSError):
                continue

    info("Config and memory data preserved")
    console.print()
