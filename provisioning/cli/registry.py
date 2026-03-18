"""Simple JSON-file registry for planes and agents.

Stores plane/agent metadata at .aios/registry.json in the project root.
"""

import json
import os
from pathlib import Path

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / ".aios"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"


def _ensure_registry() -> dict:
    """Load the registry file, creating it if it doesn't exist."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"planes": {}}


def _save_registry(data: dict) -> None:
    """Persist the registry to disk."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_plane(name: str) -> dict:
    """Register a new plane. Returns the plane record."""
    reg = _ensure_registry()
    if name in reg["planes"]:
        raise ValueError(f"Plane '{name}' already exists")
    reg["planes"][name] = {"name": name, "agents": {}}
    _save_registry(reg)
    return reg["planes"][name]


def get_plane(name: str) -> dict:
    """Look up a plane by name. Raises KeyError if not found."""
    reg = _ensure_registry()
    if name not in reg["planes"]:
        raise KeyError(f"Plane '{name}' not found. Use 'aios planes create' first.")
    return reg["planes"][name]


def add_agent_to_plane(plane_name: str, agent_id: str, owner: str, role: str = "standard") -> dict:
    """Register an agent in a plane. Returns the agent record."""
    reg = _ensure_registry()
    if plane_name not in reg["planes"]:
        raise KeyError(f"Plane '{plane_name}' not found")
    plane = reg["planes"][plane_name]
    if agent_id in plane["agents"]:
        raise ValueError(f"Agent '{agent_id}' already exists in plane '{plane_name}'")
    plane["agents"][agent_id] = {
        "id": agent_id,
        "owner": owner,
        "role": role,
        "plane": plane_name,
    }
    _save_registry(reg)
    return plane["agents"][agent_id]


def list_agents(plane_name: str) -> dict:
    """Return all agents in a plane."""
    plane = get_plane(plane_name)
    return plane.get("agents", {})


def list_planes() -> dict:
    """Return all planes."""
    reg = _ensure_registry()
    return reg.get("planes", {})
