"""Copy legacy local data into Windows user data and migrate before opening Qt views."""

import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).resolve().parents[3]
LEGACY_DATA_ROOT = PROJECT_ROOT / "backend" / "data"
SCHEMA_HEAD = "0019_build_intents"
BUNDLED_GAME_DATA = PROJECT_ROOT / "data" / "static" / "genshin-impact" / "game_data.json"


def desktop_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "GenshinPlanner" if local else Path.home() / "AppData" / "Local" / "GenshinPlanner"


def _copy_sqlite(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    try:
        target_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
    finally:
        source_connection.close()


def prepare_desktop_environment(*, destination: Path | None = None,
                                legacy_data: Path | None = None) -> Path:
    """Keep the old database untouched; install an atomic copy for native usage."""
    explicit_database = os.environ.get("GENSHIN_DATABASE_URL")
    if explicit_database:
        target_db = Path(explicit_database.removeprefix("sqlite:///")).resolve()
        destination = target_db.parent
    else:
        destination = Path(destination or desktop_data_dir()).resolve()
        target_db = destination / "app.db"
    legacy_data = Path(legacy_data or LEGACY_DATA_ROOT).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    legacy_db = legacy_data / "app.db"
    if not explicit_database and not target_db.exists() and legacy_db.is_file():
        temp_db = destination / f".app-copy-{uuid4().hex}.sqlite"
        try:
            for name in ("snapshots", "backups", "akasha"):
                folder = legacy_data / name
                if folder.is_dir():
                    shutil.copytree(folder, destination / name, dirs_exist_ok=True)
            _copy_sqlite(legacy_db, temp_db)
            connection = sqlite3.connect(temp_db)
            try:
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='snapshots'").fetchone():
                    for snapshot_id, raw_path in connection.execute("SELECT id, raw_path FROM snapshots"):
                        if not raw_path:
                            continue
                        source = Path(raw_path)
                        if not source.is_file():
                            raise FileNotFoundError(f"Snapshot file is missing: {source}")
                        try:
                            relative = source.resolve().relative_to((legacy_data / "snapshots").resolve())
                        except ValueError:
                            relative = Path(snapshot_id) / source.name
                        target = destination / "snapshots" / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not target.exists():
                            shutil.copy2(source, target)
                        connection.execute("UPDATE snapshots SET raw_path=? WHERE id=?", (str(target), snapshot_id))
                connection.commit()
            finally:
                connection.close()
            os.replace(temp_db, target_db)
            log.info("Copied legacy SQLite state to %s", target_db)
        finally:
            temp_db.unlink(missing_ok=True)
    os.environ["GENSHIN_ENVIRONMENT"] = "desktop"
    os.environ["GENSHIN_DATABASE_URL"] = f"sqlite:///{target_db.as_posix()}"
    for key, folder in (("SNAPSHOT_DIR", "snapshots"), ("BACKUP_DIR", "backups"),
                        ("AKASHA_DIR", "akasha"), ("LOG_DIR", "logs")):
        os.environ.setdefault("GENSHIN_" + key, str(destination / folder))
    if not os.environ.get("GENSHIN_GAME_DATA_PATH"):
        game_data_dir = destination / "game_data"
        game_data_dir.mkdir(parents=True, exist_ok=True)
        local_game_data = game_data_dir / "game_data.json"
        if not local_game_data.exists():
            shutil.copy2(BUNDLED_GAME_DATA, local_game_data)
        os.environ["GENSHIN_GAME_DATA_PATH"] = str(local_game_data)
    return target_db


def migrate_desktop_database() -> None:
    """Create/update schema, requiring a pre-migration backup for existing data."""
    from alembic import command
    from alembic.config import Config
    from projectg.infrastructure.configuration.settings import settings
    from projectg.infrastructure.clock.system_clock import SystemClock
    from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
    from projectg.infrastructure.backups.local_backup_gateway import LocalBackupGateway

    database = Path(settings.database_url.removeprefix("sqlite:///"))
    revision = None
    if database.is_file():
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchone():
                row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                revision = row[0] if row else None
        finally:
            connection.close()
    if revision == SCHEMA_HEAD:
        return
    has_existing_tables = False
    if database.is_file() and database.stat().st_size:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            has_existing_tables = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' LIMIT 1"
            ).fetchone() is not None
        finally:
            connection.close()
    # SQLite creates a small file before its first table is written. That is
    # an empty database, not user data; attempting to back it up through the
    # versioned backup validator prevents the initial Alembic migration.
    if has_existing_tables:
        LocalBackupGateway(
            configuration=settings, clock=SystemClock(),
            id_generator=Uuid4IdGenerator(),
        ).create_automatic_backup("PRE_DESKTOP_MIGRATION")
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    config.attributes["configure_logger"] = False
    log.info("Desktop database migration %s -> %s", revision, SCHEMA_HEAD)
    command.upgrade(config, "head")
