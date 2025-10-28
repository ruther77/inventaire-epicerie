from __future__ import annotations

import gzip
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from backup_manager import (
    BackupError,
    BinaryStatus,
    check_backup_tools,
    create_backup,
    delete_backup,
    get_backup_directory,
    list_backups,
    restore_backup,
)


def test_list_backups_returns_sorted_metadata(tmp_path):
    older = tmp_path / "older.sql.gz"
    older.write_bytes(b"old")
    newer = tmp_path / "newer.sql"
    newer.write_bytes(b"new")

    base_time = 1_600_000_000
    os.utime(older, (base_time, base_time))
    os.utime(newer, (base_time + 60, base_time + 60))

    results = list_backups(tmp_path)
    assert [meta.name for meta in results] == ["newer.sql", "older.sql.gz"]
    assert results[0].size_bytes == 3
    assert results[1].size_bytes == 3


def test_create_backup_invokes_pg_dump_and_creates_gzip(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, check, stdout, env):
        calls["cmd"] = cmd
        calls["check"] = check
        calls["stdout"] = stdout
        calls["env"] = env
        return SimpleNamespace(stdout=b"-- SQL DATA --")

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:secret@localhost:5432/epicerie",
    )
    monkeypatch.setenv("PG_DUMP_PATH", "pg_dump")
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.setenv("PSQL_PATH", "psql")
    monkeypatch.setenv("PGPASSWORD", "should-not-be-overwritten")
    monkeypatch.setattr("subprocess.run", fake_run)

    metadata = create_backup(label="Manuel", backup_dir=tmp_path)

    assert calls["cmd"][0] == "pg_dump"
    assert calls["cmd"][1].startswith("postgresql://user@localhost")
    assert calls["check"] is True
    assert calls["stdout"] == subprocess.PIPE  # type: ignore[name-defined]
    assert calls["env"]["PGPASSWORD"] == "secret"

    with gzip.open(metadata.path, "rb") as handle:
        assert handle.read() == b"-- SQL DATA --"


def test_restore_backup_invokes_psql_with_payload(monkeypatch, tmp_path):
    backup_file = tmp_path / "restore.sql.gz"
    with gzip.open(backup_file, "wb") as handle:
        handle.write(b"INSERT INTO test VALUES (1);")

    calls = {}

    def fake_run(cmd, input, check, env):
        calls["cmd"] = cmd
        calls["input"] = input
        calls["check"] = check
        calls["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@localhost:5432/epicerie",
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    restore_backup(backup_file.name, backup_dir=tmp_path, psql_path="psql")

    assert calls["cmd"][0] == "psql"
    assert calls["cmd"][1].startswith("postgresql://user@localhost")
    assert calls["input"] == b"INSERT INTO test VALUES (1);"
    assert calls["env"]["PGPASSWORD"] == "secret"


def test_delete_backup_removes_file(tmp_path):
    backup_file = tmp_path / "to_delete.sql.gz"
    backup_file.write_bytes(b"dummy")

    delete_backup(backup_file.name, backup_dir=tmp_path)

    assert not backup_file.exists()


def test_check_backup_tools_reports_resolution(monkeypatch):
    monkeypatch.delenv("PG_DUMP_BIN", raising=False)
    monkeypatch.delenv("PSQL_BIN", raising=False)
    monkeypatch.setenv("PG_DUMP_PATH", "pg_dump")
    monkeypatch.setenv("PSQL_PATH", "psql")

    def fake_which(command: str) -> str | None:
        return f"/usr/bin/{command}"

    monkeypatch.setattr("backup_manager.shutil.which", fake_which)

    pg_status, psql_status = check_backup_tools()

    assert isinstance(pg_status, BinaryStatus)
    assert pg_status.name == "pg_dump"
    assert pg_status.configured == "pg_dump"
    assert pg_status.available is True
    assert pg_status.resolved == "/usr/bin/pg_dump"
    assert "PG_DUMP_PATH" in pg_status.source

    assert isinstance(psql_status, BinaryStatus)
    assert psql_status.available is True
    assert psql_status.resolved == "/usr/bin/psql"
    assert "PSQL_PATH" in psql_status.source


def test_create_backup_without_database_url_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(BackupError):
        create_backup(backup_dir=tmp_path)


def test_create_backup_missing_pg_dump_mentions_new_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@localhost:5432/epicerie",
    )
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.delenv("PG_DUMP_PATH", raising=False)
    monkeypatch.delenv("PG_DUMP_BIN", raising=False)

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing pg_dump")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(BackupError) as excinfo:
        create_backup(backup_dir=tmp_path)

    message = str(excinfo.value)
    assert "PG_DUMP_PATH" in message
    assert "PG_DUMP_BIN" in message


def test_get_backup_directory_prefers_default_location(monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    monkeypatch.setattr(
        "backup_manager._DEFAULT_BACKUP_LOCATIONS",
        (primary, secondary),
    )

    path = get_backup_directory(create=True)

    assert path == primary
    assert primary.exists()


def test_get_backup_directory_falls_back_on_permission_error(monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    primary = tmp_path / "locked"
    secondary = tmp_path / "usable"
    monkeypatch.setattr(
        "backup_manager._DEFAULT_BACKUP_LOCATIONS",
        (primary, secondary),
    )

    original_mkdir = Path.mkdir

    def fake_mkdir(self, parents=False, exist_ok=False):  # type: ignore[override]
        if self == primary:
            raise PermissionError("denied")
        return original_mkdir(self, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir, raising=False)

    path = get_backup_directory(create=True)

    assert path == secondary
    assert secondary.exists()


def test_restore_backup_missing_psql_mentions_new_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@localhost:5432/epicerie",
    )
    monkeypatch.delenv("PSQL_PATH", raising=False)
    monkeypatch.delenv("PSQL_BIN", raising=False)

    payload_path = tmp_path / "restore.sql.gz"
    with gzip.open(payload_path, "wb") as handle:
        handle.write(b"SELECT 1;\n")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing psql")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(BackupError) as excinfo:
        restore_backup(payload_path.name, backup_dir=tmp_path)

    message = str(excinfo.value)
    assert "PSQL_PATH" in message
    assert "PSQL_BIN" in message
