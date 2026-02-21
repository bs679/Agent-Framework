"""Docker SDK wrapper for agent container management."""

from __future__ import annotations

import docker
from docker.errors import DockerException, NotFound, APIError

from provisioning.cli.output import success, error, warning


def get_client() -> docker.DockerClient | None:
    """Connect to Docker daemon, return None on failure."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException:
        error("Couldn't connect to Docker \u2014 is Docker running?")
        return None


def create_network(client: docker.DockerClient, network_name: str) -> bool:
    """Create a Docker network. Returns True on success, False on failure."""
    try:
        existing = client.networks.list(names=[network_name])
        if existing:
            warning(f"Network '{network_name}' already exists \u2014 reusing")
            return True
        client.networks.create(network_name, driver="bridge", internal=True)
        success(f"Network: {network_name}")
        return True
    except APIError as e:
        error(f"Couldn't create network '{network_name}' \u2014 {_clean_error(e)}")
        return False


def remove_network(client: docker.DockerClient, network_name: str) -> bool:
    """Remove a Docker network."""
    try:
        networks = client.networks.list(names=[network_name])
        for net in networks:
            net.remove()
        return True
    except APIError as e:
        error(f"Couldn't remove network '{network_name}' \u2014 {_clean_error(e)}")
        return False


def create_container(
    client: docker.DockerClient,
    name: str,
    network: str,
    volumes: dict,
    env_file_path: str | None = None,
    environment: dict | None = None,
    image: str = "ghcr.io/openclaw/openclaw:latest",
) -> docker.models.containers.Container | None:
    """Create (but don't start) an agent container. Idempotent."""
    try:
        existing = client.containers.get(name)
        warning(f"Container '{name}' already exists \u2014 skipping creation")
        return existing
    except NotFound:
        pass

    env_vars = {}
    if env_file_path:
        env_vars.update(_parse_env_file(env_file_path))
    if environment:
        env_vars.update(environment)

    try:
        container = client.containers.create(
            image=image,
            name=name,
            network=network,
            volumes=volumes,
            environment=env_vars,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
        )
        success("Container created")
        return container
    except APIError as e:
        error(f"Couldn't create container '{name}' \u2014 {_clean_error(e)}")
        return None


def start_container(
    client: docker.DockerClient, name: str
) -> bool:
    """Start a container by name."""
    try:
        container = client.containers.get(name)
        if container.status == "running":
            warning(f"Container '{name}' is already running")
            return True
        container.start()
        return True
    except NotFound:
        error(f"Container '{name}' not found")
        return False
    except APIError as e:
        error(f"Couldn't start container '{name}' \u2014 {_clean_error(e)}")
        return False


def stop_container(client: docker.DockerClient, name: str) -> bool:
    """Stop a container by name."""
    try:
        container = client.containers.get(name)
        if container.status != "running":
            return True
        container.stop(timeout=30)
        return True
    except NotFound:
        return True
    except APIError as e:
        error(f"Couldn't stop container '{name}' \u2014 {_clean_error(e)}")
        return False


def remove_container(client: docker.DockerClient, name: str) -> bool:
    """Stop and remove a container."""
    try:
        container = client.containers.get(name)
        if container.status == "running":
            container.stop(timeout=30)
        container.remove()
        return True
    except NotFound:
        return True
    except APIError as e:
        error(f"Couldn't remove container '{name}' \u2014 {_clean_error(e)}")
        return False


def restart_container(client: docker.DockerClient, name: str) -> bool:
    """Restart a container."""
    try:
        container = client.containers.get(name)
        container.restart(timeout=30)
        return True
    except NotFound:
        error(f"Container '{name}' not found")
        return False
    except APIError as e:
        error(f"Couldn't restart container '{name}' \u2014 {_clean_error(e)}")
        return False


def get_container_status(client: docker.DockerClient, name: str) -> str:
    """Get container status string. Returns 'stopped' if not found."""
    try:
        container = client.containers.get(name)
        return container.status
    except NotFound:
        return "stopped"
    except APIError:
        return "stopped"


def get_container_details(
    client: docker.DockerClient, name: str
) -> dict | None:
    """Get detailed container info: status, uptime, health."""
    try:
        container = client.containers.get(name)
        attrs = container.attrs
        state = attrs.get("State", {})

        health = "no health check configured"
        if "Health" in state:
            health = state["Health"].get("Status", "unknown")

        return {
            "status": container.status,
            "started_at": state.get("StartedAt", "unknown"),
            "finished_at": state.get("FinishedAt", ""),
            "health": health,
            "image": attrs.get("Config", {}).get("Image", "unknown"),
        }
    except NotFound:
        return None
    except APIError:
        return None


def get_container_logs(
    client: docker.DockerClient,
    name: str,
    tail: int = 50,
    follow: bool = False,
) -> str | None:
    """Get container logs. Filters sensitive values."""
    sensitive_keywords = ["SECRET", "KEY", "TOKEN", "PASSWORD"]

    try:
        container = client.containers.get(name)
        if follow:
            return container.logs(stream=True, follow=True, tail=tail)
        logs = container.logs(tail=tail).decode("utf-8", errors="replace")
        return _filter_sensitive_lines(logs, sensitive_keywords)
    except NotFound:
        error(f"Container '{name}' not found")
        return None
    except APIError as e:
        error(f"Couldn't get logs for '{name}' \u2014 {_clean_error(e)}")
        return None


def _filter_sensitive_lines(logs: str, keywords: list[str]) -> str:
    """Replace lines containing sensitive keywords."""
    filtered = []
    for line in logs.splitlines():
        if any(kw in line.upper() for kw in keywords):
            filtered.append("[sensitive \u2014 not shown]")
        else:
            # Strip Docker timestamp prefix (first 31 chars if present)
            cleaned = _clean_timestamp(line)
            filtered.append(cleaned)
    return "\n".join(filtered)


def _clean_timestamp(line: str) -> str:
    """Remove Docker's default timestamp prefix from log lines."""
    # Docker log format: "2024-01-15T10:30:00.123456789Z message"
    if len(line) > 31 and line[4] == "-" and line[10] == "T":
        return line[31:].lstrip()
    return line


def _parse_env_file(path: str) -> dict[str, str]:
    """Parse a .env file into a dict."""
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env


def _clean_error(e: Exception) -> str:
    """Extract a human-readable message from a Docker API error."""
    msg = str(e)
    # Strip HTTP status codes and JSON wrapping
    if hasattr(e, "explanation"):
        return e.explanation
    if ":" in msg:
        return msg.split(":", 1)[-1].strip()
    return msg
