"""`aios planes` subcommands — create and manage agent planes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from provisioning.cli import docker_client as dc
from provisioning.cli.output import (
    console,
    success,
    error,
    info,
    print_agent_row,
)

app = typer.Typer(help="Manage agent planes")

PLANES_DIR = Path("planes")


def _planes_dir() -> Path:
    PLANES_DIR.mkdir(parents=True, exist_ok=True)
    return PLANES_DIR


def _load_plane(name: str) -> dict | None:
    path = _planes_dir() / f"{name}.json"
    if not path.is_file():
        error(f"Plane '{name}' not found \u2014 run 'aios planes create --name {name}' first")
        return None
    return json.loads(path.read_text())


def _save_plane(name: str, data: dict) -> None:
    path = _planes_dir() / f"{name}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")


@app.command("create")
def create(
    name: str = typer.Option(..., help="Name for the new plane"),
) -> None:
    """Create a new agent plane with its Docker network."""
    plane_file = _planes_dir() / f"{name}.json"
    if plane_file.is_file():
        error(f"Plane '{name}' already exists at {plane_file}")
        raise typer.Exit(1)

    client = dc.get_client()
    if client is None:
        raise typer.Exit(1)

    network_name = f"{name}-net"
    plane_data = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": [],
        "docker_network": network_name,
    }

    if not dc.create_network(client, network_name):
        raise typer.Exit(1)

    _save_plane(name, plane_data)

    console.print()
    success(f"Plane '{name}' created")
    info(f"Network: {network_name}")
    info(f"Config: {plane_file}")


@app.command("status")
def status() -> None:
    """Show status of all planes and their agents."""
    planes_dir = _planes_dir()
    plane_files = sorted(planes_dir.glob("*.json"))

    if not plane_files:
        from provisioning.cli.output import stopped
        stopped("No planes configured")
        return

    client = dc.get_client()

    for pf in plane_files:
        try:
            plane = json.loads(pf.read_text())
        except (json.JSONDecodeError, OSError):
            error(f"Couldn't read plane config: {pf}")
            continue

        plane_name = plane.get("name", pf.stem)
        agents = plane.get("agents", [])

        console.print(f"\n[bold]{plane_name}[/bold] ({plane.get('docker_network', 'unknown')})")

        if not agents:
            from provisioning.cli.output import stopped
            stopped("No agents in this plane")
            continue

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
