"""Tests for the agent memory backup module (provisioning/cli/backup)."""

from __future__ import annotations

import io
import json
import tarfile
from datetime import date

import pytest
from cryptography.fernet import Fernet

from provisioning.cli.backup import run_backup


@pytest.fixture()
def project(tmp_path):
    """A minimal fake project tree: two agents, one without memory."""
    memory = tmp_path / "agents" / "president-dave" / "memory"
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("# grievance notes\nWaterbury #24-117\n")
    (memory / "notes.md").write_text("call sectreas re: audit\n")

    (tmp_path / "agents" / "staff4-jordan").mkdir(parents=True)  # no memory dir

    aios = tmp_path / ".aios"
    aios.mkdir()
    (aios / "registry.json").write_text('{"planes": {}}')
    return tmp_path


def _extract_names(tar_bytes: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        return sorted(m.name for m in tar.getmembers() if m.isfile())


class TestRunBackup:
    def test_encrypted_backup_roundtrip(self, project):
        key = Fernet.generate_key().decode()
        report = run_backup(project, fernet_key=key, backup_date=date(2026, 7, 6))

        assert report["encrypted"] is True
        assert [a["agent_id"] for a in report["agents"]] == ["president-dave"]
        assert report["skipped"] == ["staff4-jordan"]

        backup_dir = project / "backups" / "2026-07-06"
        enc_file = backup_dir / "memory-president-dave.tar.gz.enc"
        assert enc_file.exists()

        # ciphertext must not contain the plaintext
        raw = enc_file.read_bytes()
        assert b"Waterbury" not in raw

        # decrypts back to a tar with the memory files
        decrypted = Fernet(key.encode()).decrypt(raw)
        names = _extract_names(decrypted)
        assert "president-dave/memory/MEMORY.md" in names
        assert "president-dave/memory/notes.md" in names

    def test_unencrypted_when_no_key(self, project):
        report = run_backup(project, backup_date=date(2026, 7, 6))
        assert report["encrypted"] is False
        plain = project / "backups" / "2026-07-06" / "memory-president-dave.tar.gz"
        assert plain.exists()
        assert "president-dave/memory/MEMORY.md" in _extract_names(plain.read_bytes())

    def test_manifest_and_registry_copied(self, project):
        run_backup(project, backup_date=date(2026, 7, 6))
        backup_dir = project / "backups" / "2026-07-06"
        assert (backup_dir / "registry.json").read_text() == '{"planes": {}}'
        manifest = json.loads((backup_dir / "MANIFEST.json").read_text())
        assert manifest["date"] == "2026-07-06"
        assert manifest["registry"] == "registry.json"

    def test_rotation_removes_only_old_dated_dirs(self, project):
        base = project / "backups"
        (base / "2026-05-01").mkdir(parents=True)  # 66 days old — rotated
        (base / "2026-06-20").mkdir()              # 16 days old — kept
        (base / "keep-me").mkdir()                 # not a dated dir — kept

        report = run_backup(
            project, retention_days=30, backup_date=date(2026, 7, 6)
        )
        assert report["rotated_out"] == ["2026-05-01"]
        assert not (base / "2026-05-01").exists()
        assert (base / "2026-06-20").exists()
        assert (base / "keep-me").exists()

    def test_empty_project_produces_empty_report(self, tmp_path):
        report = run_backup(tmp_path, backup_date=date(2026, 7, 6))
        assert report["agents"] == []
        assert report["skipped"] == []
        assert (tmp_path / "backups" / "2026-07-06" / "MANIFEST.json").exists()
