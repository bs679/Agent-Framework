"""Structured audit log for provisioning operations.

Appends one JSON object per line to ``.aios/provisioning.log`` so
provisioning success/failure rates can be tracked over time (observability
baseline, PROJECT_REVIEW P2 #10). Events are content-free — agent ids and
error strings only, never config contents or secrets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / ".aios"
LOG_FILE = LOG_DIR / "provisioning.log"


def log_event(event: str, agent_id: str | None = None, *, plane: str | None = None,
              ok: bool = True, error: str | None = None, **extra: object) -> None:
    """Append a provisioning event. Never raises — logging must not break the CLI."""
    record: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "ok": ok,
    }
    if agent_id is not None:
        record["agent_id"] = agent_id
    if plane is not None:
        record["plane"] = plane
    if error is not None:
        record["error"] = error
    record.update(extra)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass
