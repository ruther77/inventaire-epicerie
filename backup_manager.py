"""Utilities for managing database backup files.

This module centralises backup related operations used by the Streamlit
administration dashboard.  It exposes helpers to create, inspect, restore and
remove PostgreSQL dumps stored on disk.  Each function is intentionally small
and testable so that the UI can simply call them without having to mock any
Streamlit specific behaviour.
"""
from __future__ import annotations

import gzip
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url


class BackupError(RuntimeError):
    """Raised when a backup operation cannot be completed."""


@dataclass(frozen=True, slots=True)
class BackupMetadata:
    """Simple container describing a backup file present on disk."""

    name: str
    path: Path
    size_bytes: int
    created_at: datetime

    @property
    def size_mb(self) -> float:
        """Human friendly representation in megabytes."""

        return self.size_bytes / (1024 * 1024)


_DEFAULT_BACKUP_LOCATIONS: Tuple[Path, ...] = (
    Path("/app/backups"),
    Path("backups"),
)


@dataclass(frozen=True, slots=True)
class BinaryStatus:
    """Describe how a required external command is resolved."""

    name: str
    configured: str
    resolved: Optional[str]
    source: str

    @property
    def available(self) -> bool:
        return self.resolved is not None


def get_backup_directory(
    directory: str | os.PathLike[str] | None = None,
    *,
    create: bool = True,
) -> Path:
    """Return the directory used to store backup files.

    Args:
        directory: Optional override path.  When omitted the BACKUP_DIR
            environment variable is used, or ``/app/backups`` (falling back to
            ``./backups`` if the former cannot be created).
        create: Whether the directory should be created when missing.

    Returns:
        A :class:`~pathlib.Path` object pointing to the backup folder.
    """

    candidates: Tuple[Path, ...]
    if directory is not None:
        candidates = (Path(directory),)
    else:
        env_directory = os.getenv("BACKUP_DIR")
        if env_directory:
            candidates = (Path(env_directory),)
        else:
            candidates = _DEFAULT_BACKUP_LOCATIONS

    for candidate in candidates:
        path = candidate
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                continue
        return path

    # If all automatic locations failed because of permissions, fall back to a
    # relative directory that Streamlit can create in the working tree.
    fallback = Path("backups")
    if create:
        fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _select_binary(
    explicit: Optional[str],
    *,
    env_vars: Tuple[str, ...],
    default: str,
    argument_label: str,
) -> Tuple[str, str]:
    """Return the binary path and describe how it was resolved."""

    if explicit:
        return explicit, f"l'argument {argument_label}"

    for env_var in env_vars:
        value = os.getenv(env_var)
        if value:
            return value, f"la variable d'environnement {env_var}"

    return default, "la valeur par défaut du système"


def _resolve_binary_location(command: str) -> Optional[str]:
    """Return the absolute location of *command* if available."""

    path = Path(command)
    if path.is_absolute() or path.parent != Path("."):
        if path.exists() and os.access(path, os.X_OK):
            return str(path.resolve())
        return None

    return shutil.which(command)


def _normalise_database_url(database_url: str) -> Tuple[str, Optional[str]]:
    """Return a ``postgresql://`` URL compatible with psql/pg_dump.

    SQLAlchemy URLs can embed the driver name (``postgresql+psycopg2``) which
    is not understood by the PostgreSQL command line tools.  The function also
    extracts the password so it can be provided via the ``PGPASSWORD``
    environment variable instead of appearing on the command line.
    """

    original = make_url(database_url)
    driver = original.drivername.split("+")[0]

    clean_url = URL.create(
        driver,
        username=original.username,
        password=None,
        host=original.host,
        port=original.port,
        database=original.database,
        query=original.query,
    )

    return clean_url.render_as_string(hide_password=False), original.password


def _prepare_env(password: Optional[str]) -> dict:
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def _build_backup_name(label: Optional[str]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not label:
        return f"epicerie_backup_{timestamp}.sql.gz"

    cleaned = re.sub(r"[^0-9A-Za-z_-]+", "-", label).strip("-_")
    cleaned = cleaned.lower()
    if not cleaned:
        return f"epicerie_backup_{timestamp}.sql.gz"

    return f"epicerie_backup_{timestamp}_{cleaned}.sql.gz"


def list_backups(
    directory: str | os.PathLike[str] | None = None,
) -> List[BackupMetadata]:
    """Return backup metadata sorted from newest to oldest."""

    backup_dir = get_backup_directory(directory, create=False)
    if not backup_dir.exists():
        return []

    entries: List[BackupMetadata] = []
    for item in backup_dir.iterdir():
        if not item.is_file():
            continue
        if not item.name.endswith((".sql", ".sql.gz")):
            continue

        stat = item.stat()
        created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        entries.append(
            BackupMetadata(
                name=item.name,
                path=item,
                size_bytes=stat.st_size,
                created_at=created,
            )
        )

    entries.sort(key=lambda meta: meta.created_at, reverse=True)
    return entries


def _resolve_backup_path(
    filename: str,
    directory: str | os.PathLike[str] | None = None,
) -> Path:
    backup_dir = get_backup_directory(directory, create=False)
    path = backup_dir / filename
    if not path.exists():
        raise BackupError(f"Le fichier de sauvegarde '{filename}' est introuvable.")
    if not path.is_file():
        raise BackupError(f"Le chemin '{filename}' n'est pas un fichier de sauvegarde valide.")
    return path


def create_backup(
    *,
    label: Optional[str] = None,
    database_url: Optional[str] = None,
    backup_dir: str | os.PathLike[str] | None = None,
    pg_dump_path: Optional[str] = None,
) -> BackupMetadata:
    """Create a new backup using ``pg_dump`` and return its metadata."""

    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise BackupError("Aucune configuration de base de données trouvée.")

    normalised_url, password = _normalise_database_url(database_url)
    env = _prepare_env(password)

    pg_dump_path, pg_dump_source = _select_binary(
        pg_dump_path,
        env_vars=("PG_DUMP_PATH", "PG_DUMP_BIN"),
        default="pg_dump",
        argument_label="pg_dump_path",
    )

    backup_directory = get_backup_directory(backup_dir, create=True)
    filename = _build_backup_name(label)
    target_path = backup_directory / filename

    try:
        completed = subprocess.run(
            [pg_dump_path, normalised_url],
            check=True,
            stdout=subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise BackupError(
            "L'outil 'pg_dump' est introuvable (chemin utilisé : "
            f"{pg_dump_path!r} depuis {pg_dump_source}). Assurez-vous que le "
            "client PostgreSQL est installé et que l'utilitaire est présent "
            "dans le PATH ou définissez les variables d'environnement "
            "PG_DUMP_PATH/PG_DUMP_BIN."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise BackupError("La commande pg_dump a échoué.") from exc

    with gzip.open(target_path, "wb") as buffer:
        buffer.write(completed.stdout)

    stat = target_path.stat()
    return BackupMetadata(
        name=filename,
        path=target_path,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


def delete_backup(
    filename: str,
    *,
    backup_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Delete an existing backup file."""

    path = _resolve_backup_path(filename, directory=backup_dir)
    path.unlink()


def restore_backup(
    filename: str,
    *,
    database_url: Optional[str] = None,
    backup_dir: str | os.PathLike[str] | None = None,
    psql_path: Optional[str] = None,
) -> None:
    """Restore the database using the provided backup file."""

    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise BackupError("Aucune configuration de base de données trouvée.")

    normalised_url, password = _normalise_database_url(database_url)
    env = _prepare_env(password)

    path = _resolve_backup_path(filename, directory=backup_dir)
    psql_path, psql_source = _select_binary(
        psql_path,
        env_vars=("PSQL_PATH", "PSQL_BIN"),
        default="psql",
        argument_label="psql_path",
    )

    if path.suffix == ".gz":
        with gzip.open(path, "rb") as buffer:
            payload = buffer.read()
    else:
        payload = path.read_bytes()

    try:
        subprocess.run(
            [psql_path, normalised_url],
            input=payload,
            check=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise BackupError(
            "L'outil 'psql' est introuvable (chemin utilisé : "
            f"{psql_path!r} depuis {psql_source}). Assurez-vous que le client "
            "PostgreSQL est installé et que l'utilitaire est présent dans le "
            "PATH ou définissez les variables d'environnement PSQL_PATH/PSQL_BIN."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise BackupError("La commande psql a échoué lors de la restauration.") from exc


def check_backup_tools(
    *,
    pg_dump_path: Optional[str] = None,
    psql_path: Optional[str] = None,
) -> Tuple[BinaryStatus, BinaryStatus]:
    """Return diagnostic information about pg_dump and psql availability."""

    pg_dump, pg_dump_source = _select_binary(
        pg_dump_path,
        env_vars=("PG_DUMP_PATH", "PG_DUMP_BIN"),
        default="pg_dump",
        argument_label="pg_dump_path",
    )
    psql, psql_source = _select_binary(
        psql_path,
        env_vars=("PSQL_PATH", "PSQL_BIN"),
        default="psql",
        argument_label="psql_path",
    )

    pg_dump_resolved = _resolve_binary_location(pg_dump)
    psql_resolved = _resolve_binary_location(psql)

    return (
        BinaryStatus("pg_dump", pg_dump, pg_dump_resolved, pg_dump_source),
        BinaryStatus("psql", psql, psql_resolved, psql_source),
    )


__all__ = [
    "BackupError",
    "BackupMetadata",
    "BinaryStatus",
    "check_backup_tools",
    "create_backup",
    "delete_backup",
    "get_backup_directory",
    "list_backups",
    "restore_backup",
]
