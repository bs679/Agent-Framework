"""Agent memory backup — local, encrypted, rotated.

Implements PROJECT_REVIEW P2 #9: a daily backup of ``agents/*/memory``
volumes to a local encrypted archive, exposed as ``aios planes backup``.

Layout::

    backups/
      2026-07-06/
        memory-president-dave.tar.gz.enc
        memory-staff4-jordan.tar.gz.enc
        registry.json
        MANIFEST.json

Encryption
----------
Archives are encrypted with Fernet using the key in ``AIOS_BACKUP_KEY``.
Agent memory contains sensitive union data, so running without a key
prints a loud warning and marks the manifest ``encrypted: false``.

Restore an encrypted archive with::

    python -c "import sys; from cryptography.fernet import Fernet; \\
      sys.stdout.buffer.write(Fernet(sys.argv[1].encode()).decrypt(open(sys.argv[2],'rb').read()))" \\
      "$AIOS_BACKUP_KEY" memory-president-dave.tar.gz.enc > memory.tar.gz

The companion ``scripts/backup.sh`` covers the PostgreSQL dump; this module
covers agent memory + the plane registry.
"""

from __future__ import annotations

import io
import json
import shutil
import tarfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _tar_directory_bytes(root: Path, arcname: str) -> bytes:
    """Create a tar.gz of *root* (stored under *arcname*) in memory."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(root, arcname=arcname)
    return buf.getvalue()


def run_backup(
    project_root: Path,
    output_base: Path | None = None,
    retention_days: int = 30,
    fernet_key: str | None = None,
    backup_date: date | None = None,
) -> dict:
    """Back up all agent memory dirs and the registry. Returns a report dict."""
    backup_date = backup_date or date.today()
    output_base = output_base or (project_root / "backups")
    backup_dir = output_base / backup_date.isoformat()
    backup_dir.mkdir(parents=True, exist_ok=True)

    fernet = None
    if fernet_key:
        from cryptography.fernet import Fernet

        fernet = Fernet(fernet_key.encode())

    report: dict = {
        "date": backup_date.isoformat(),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "encrypted": fernet is not None,
        "backup_dir": str(backup_dir),
        "agents": [],
        "skipped": [],
    }

    agents_dir = project_root / "agents"
    if agents_dir.is_dir():
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            memory_dir = agent_dir / "memory"
            if not memory_dir.is_dir():
                report["skipped"].append(agent_dir.name)
                continue

            data = _tar_directory_bytes(memory_dir, f"{agent_dir.name}/memory")
            suffix = ".tar.gz.enc" if fernet else ".tar.gz"
            if fernet:
                data = fernet.encrypt(data)
            out_path = backup_dir / f"memory-{agent_dir.name}{suffix}"
            out_path.write_bytes(data)
            report["agents"].append(
                {"agent_id": agent_dir.name, "file": out_path.name, "bytes": len(data)}
            )

    # Registry (plane/agent metadata — not sensitive, kept plain for recovery)
    registry_file = project_root / ".aios" / "registry.json"
    if registry_file.is_file():
        shutil.copyfile(registry_file, backup_dir / "registry.json")
        report["registry"] = "registry.json"

    (backup_dir / "MANIFEST.json").write_text(json.dumps(report, indent=2) + "\n")

    # Rotation: remove dated backup dirs older than retention_days
    cutoff = backup_date - timedelta(days=retention_days)
    removed: list[str] = []
    for entry in output_base.iterdir():
        if not entry.is_dir():
            continue
        try:
            entry_date = date.fromisoformat(entry.name)
        except ValueError:
            continue  # not a dated backup dir — leave it alone
        if entry_date < cutoff:
            shutil.rmtree(entry)
            removed.append(entry.name)
    report["rotated_out"] = removed

    return report
