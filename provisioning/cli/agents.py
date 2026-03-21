"""aios agents — subcommands for managing individual agents."""

import secrets
import sys
import time
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


@agents.command("upgrade")
@click.option("--plane", required=True, help="Plane containing the agents")
@click.option("--agent", default=None, help="Upgrade a single agent by ID (omit for all)")
@click.option("--image", default="openclaw/openclaw:latest", show_default=True,
              help="Docker image to upgrade to")
def upgrade(plane, agent, image):
    """Rolling upgrade: pull latest image and recreate agent containers.

    Upgrades agents one at a time. Stops immediately on the first failure
    so a bad image does not take down the entire plane.

    Examples:
        aios agents upgrade --plane chca-agents
        aios agents upgrade --plane chca-agents --agent president-dave
    """
    try:
        import docker
        from docker.errors import DockerException, NotFound, APIError
    except ImportError:
        click.echo("Error: docker SDK not installed. Run: pip install docker", err=True)
        sys.exit(1)

    try:
        client = docker.from_env()
        client.ping()
    except DockerException:
        click.echo("Error: cannot connect to Docker — is Docker running?", err=True)
        sys.exit(1)

    # Resolve agent list
    try:
        agents_dict = list_agents(plane)
    except KeyError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not agents_dict:
        click.echo(f"No agents found in plane '{plane}'.")
        sys.exit(0)

    if agent:
        if agent not in agents_dict:
            click.echo(f"Error: agent '{agent}' not found in plane '{plane}'", err=True)
            sys.exit(1)
        target_agents = {agent: agents_dict[agent]}
    else:
        target_agents = agents_dict

    click.echo(f"\nUpgrading {len(target_agents)} agent(s) in plane '{plane}'")
    click.echo(f"Target image: {image}\n")

    # 1. Pull latest image
    click.echo(f"Pulling {image}...")
    try:
        client.images.pull(image)
        click.echo(f"  ✓ Pulled {image}")
    except APIError as exc:
        click.echo(f"  ! Failed to pull image: {exc}", err=True)
        sys.exit(1)

    results: list[dict] = []

    for agent_id, agent_record in target_agents.items():
        container_name = f"openclaw-{agent_id}"
        click.echo(f"\n  Upgrading {agent_id}...")

        # a. Health check before starting
        try:
            existing = client.containers.get(container_name)
            pre_status = existing.status
        except NotFound:
            pre_status = "not_found"

        click.echo(f"    Pre-upgrade status: {pre_status}")

        # b. Stop existing container
        click.echo(f"    Stopping {container_name}...")
        try:
            existing = client.containers.get(container_name)
            if existing.status == "running":
                existing.stop(timeout=30)
            # c. Remove old container
            existing.remove()
            click.echo(f"    ✓ Removed old container")
        except NotFound:
            click.echo(f"    ~ No existing container to remove")
        except APIError as exc:
            click.echo(f"    ! Could not remove container: {exc}", err=True)
            results.append({"agent_id": agent_id, "result": "failed", "error": str(exc)})
            click.echo(f"\n  Stopping upgrade — {agent_id} failed. Check logs before retrying.")
            break

        # d. Re-create with same config
        agent_dir = PROJECT_ROOT / "agents" / agent_id
        config_dir = agent_dir / "config"
        memory_dir = agent_dir / "memory"
        env_path = agent_dir / ".env"

        volumes: dict = {}
        if config_dir.exists():
            volumes[str(config_dir.resolve())] = {"bind": "/app/config", "mode": "ro"}
        if memory_dir.exists():
            volumes[str(memory_dir.resolve())] = {"bind": "/app/memory", "mode": "rw"}

        env_vars: dict[str, str] = {
            "AGENT_ID": agent_id,
            "PLANE_NAME": plane,
            "OLLAMA_HOST": "host.docker.internal:11434",
        }
        if env_path.exists():
            env_vars.update(_parse_env_file(env_path))

        try:
            new_container = client.containers.create(
                image=image,
                name=container_name,
                volumes=volumes,
                environment=env_vars,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
            )
        except APIError as exc:
            click.echo(f"    ! Could not create container: {exc}", err=True)
            results.append({"agent_id": agent_id, "result": "failed", "error": str(exc)})
            click.echo(f"\n  Stopping upgrade — {agent_id} failed. Fix the issue before retrying.")
            break

        # e. Start new container
        try:
            new_container.start()
        except APIError as exc:
            click.echo(f"    ! Could not start container: {exc}", err=True)
            results.append({"agent_id": agent_id, "result": "failed", "error": str(exc)})
            click.echo(f"\n  Stopping upgrade — {agent_id} failed. Check image and config.")
            break

        # f. Wait up to 60s for health check to pass (or just for running status)
        click.echo(f"    Waiting for health check (up to 60s)...")
        deadline = time.monotonic() + 60
        healthy = False
        while time.monotonic() < deadline:
            new_container.reload()
            state = new_container.attrs.get("State", {})
            status = new_container.status
            health = state.get("Health", {}).get("Status", "none")

            if health == "healthy":
                healthy = True
                break
            elif health == "none" and status == "running":
                # No HEALTHCHECK defined — running is enough
                healthy = True
                break
            elif health in ("unhealthy",):
                break
            time.sleep(3)

        if healthy:
            click.echo(f"    ✓ {agent_id} upgraded successfully")
            results.append({"agent_id": agent_id, "result": "upgraded"})
        else:
            final_health = new_container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
            click.echo(f"    ! {agent_id} health check did not pass (status: {final_health})", err=True)
            results.append({"agent_id": agent_id, "result": "failed", "error": f"health: {final_health}"})
            click.echo(f"\n  Stopping upgrade — {agent_id} failed. Check: aios agents logs --agent {agent_id}")
            break

    # g. Final report
    click.echo(f"\n{'─' * 50}")
    click.echo("Upgrade summary:")
    for r in results:
        icon = "✓" if r["result"] == "upgraded" else "!"
        msg = f"  {icon} {r['agent_id']}: {r['result']}"
        if "error" in r:
            msg += f" ({r['error']})"
        click.echo(msg)

    failed = [r for r in results if r["result"] == "failed"]
    not_attempted = [a for a in target_agents if a not in {r["agent_id"] for r in results}]
    if not_attempted:
        click.echo(f"\n  Not attempted ({len(not_attempted)}): {', '.join(not_attempted)}")

    if failed:
        click.echo(f"\n  Upgrade incomplete — {len(failed)} agent(s) failed.")
        sys.exit(1)
    else:
        click.echo(f"\n  All {len(results)} agent(s) upgraded successfully.")


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict (skips comments and blanks)."""
    env: dict[str, str] = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    except OSError:
        pass
    return env


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
