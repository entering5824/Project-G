"""SQLite-specific backup validation, copy, and restore mechanics."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from projectg.application.backups.errors import BackupError
from projectg.application.backups.policy import DB_SCHEMA_HEAD, SUPPORTED_DB_SCHEMAS

REQUIRED_DATABASE_TABLES = {
    "accounts", "snapshots", "snapshot_characters", "snapshot_weapons",
    "snapshot_artifacts", "snapshot_teams", "history_events", "artifact_evaluations",
}


@dataclass(frozen=True)
class DatabaseValidation:
    schema: str | None
    tables: tuple[str, ...]


def sqlite_path(url: str) -> Path:
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        raise BackupError(
            "BACKUP_DATABASE_UNSUPPORTED",
            "Backup currently requires a file-based SQLite database.",
        )
    return Path(url.removeprefix("sqlite:///" )).resolve()


class SqliteBackupDatabase:
    def __init__(self, database_url: str, snapshot_dir: Path):
        self.database_url = database_url
        self.database = sqlite_path(database_url)
        self.snapshot_dir = Path(snapshot_dir).resolve()

    def validate(self, path: Path | None = None) -> DatabaseValidation:
        database = Path(path or self.database)
        if not database.is_file():
            raise BackupError("BACKUP_DATABASE_MISSING", "The local database file does not exist.")
        try:
            connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
            try:
                check = connection.execute("PRAGMA integrity_check").fetchone()[0]
                if check != "ok":
                    raise BackupError(
                        "BACKUP_DATABASE_CORRUPT", "SQLite integrity check failed.", {"result": check})
                tables = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                schema = (
                    connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                    if "alembic_version" in tables else None
                )
                if not REQUIRED_DATABASE_TABLES.issubset(tables):
                    raise BackupError(
                        "BACKUP_SCHEMA_INCOMPATIBLE",
                        "Database does not contain the M6 data schema.",
                        {"tables": sorted(tables)},
                    )
                if (
                    schema in SUPPORTED_DB_SCHEMAS - {
                        "0007_snapshot_path_relocation", "0008_snapshot_reference_foreign_keys"
                    }
                    and "idempotency_receipts" not in tables
                ):
                    raise BackupError(
                        "BACKUP_SCHEMA_INCOMPATIBLE",
                        "Database is missing the target import idempotency table.",
                    )
                if (
                    schema in {
                        "0011_target_presets", "0012_inventory_reserves", "0013_plan_runs_today_state",
                        "0014_planner_teams", "0015_account_availability_settings", DB_SCHEMA_HEAD,
                    }
                    and "character_target_presets" not in tables
                ):
                    raise BackupError(
                        "BACKUP_SCHEMA_INCOMPATIBLE", "Database is missing character target presets.")
                if (
                    schema in {"0013_plan_runs_today_state", "0014_planner_teams",
                               "0015_account_availability_settings", DB_SCHEMA_HEAD}
                    and not {"plan_runs", "today_state"}.issubset(tables)
                ):
                    raise BackupError(
                        "BACKUP_SCHEMA_INCOMPATIBLE", "Database is missing persisted Today planning state.")
                if (
                    schema in {"0014_planner_teams", "0015_account_availability_settings", DB_SCHEMA_HEAD}
                    and "planner_teams" not in tables
                ):
                    raise BackupError(
                        "BACKUP_SCHEMA_INCOMPATIBLE", "Database is missing planner team configuration.")
                if schema == DB_SCHEMA_HEAD:
                    columns = {row[1] for row in connection.execute("PRAGMA table_info(planner_teams)")}
                    if "is_primary" not in columns:
                        raise BackupError(
                            "BACKUP_SCHEMA_INCOMPATIBLE", "Database is missing primary planner team state.")

                fk_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
                if fk_issues:
                    raise BackupError(
                        "BACKUP_DATABASE_LOGIC_INVALID",
                        "Database contains broken foreign-key references.",
                        {"foreignKeyViolations": len(fk_issues)},
                    )

                checks = {
                    "account current snapshot": """SELECT COUNT(*) FROM accounts a LEFT JOIN snapshots s
                        ON s.id=a.current_snapshot_id WHERE a.current_snapshot_id IS NOT NULL
                        AND (s.id IS NULL OR s.account_id != a.id)""",
                    "snapshot predecessor": """SELECT COUNT(*) FROM snapshots s LEFT JOIN snapshots p
                        ON p.id=s.previous_snapshot_id WHERE s.previous_snapshot_id IS NOT NULL
                        AND (p.id IS NULL OR p.account_id != s.account_id)""",
                    "character progression values": """SELECT COUNT(*) FROM snapshot_characters
                        WHERE level NOT BETWEEN 0 AND 100 OR ascension NOT BETWEEN 0 AND 6
                        OR constellation NOT BETWEEN 0 AND 6 OR talent_auto NOT BETWEEN 0 AND 15
                        OR talent_skill NOT BETWEEN 0 AND 15 OR talent_burst NOT BETWEEN 0 AND 15""",
                    "weapon progression values": """SELECT COUNT(*) FROM snapshot_weapons
                        WHERE level NOT BETWEEN 0 AND 90 OR ascension NOT BETWEEN 0 AND 6
                        OR refinement NOT BETWEEN 0 AND 5""",
                    "artifact progression values": """SELECT COUNT(*) FROM snapshot_artifacts
                        WHERE rarity NOT BETWEEN 0 AND 5 OR level NOT BETWEEN 0 AND 20""",
                    "artifact character relation": """SELECT COUNT(*) FROM snapshot_artifacts a LEFT JOIN snapshot_characters c
                        ON c.snapshot_id=a.snapshot_id AND c.character_key=a.character_key WHERE c.character_key IS NULL""",
                    "equipped weapon relation": """SELECT COUNT(*) FROM snapshot_characters c LEFT JOIN snapshot_weapons w
                        ON w.snapshot_id=c.snapshot_id AND w.weapon_instance_id=c.equipped_weapon_instance_id
                        WHERE c.equipped_weapon_instance_id IS NOT NULL AND w.weapon_instance_id IS NULL""",
                    "team member relation": """SELECT COUNT(*) FROM snapshot_teams t, json_each(t.members_json) m
                        LEFT JOIN snapshot_characters c ON c.snapshot_id=t.snapshot_id AND c.character_key=m.value
                        WHERE m.type != 'text' OR c.character_key IS NULL""",
                    "artifact evaluation status": """SELECT COUNT(*) FROM artifact_evaluations
                        WHERE status NOT IN ('PENDING','CONFIRMED','REJECTED','SUPERSEDED')""",
                    "artifact evaluation source": """SELECT COUNT(*) FROM artifact_evaluations
                        WHERE source NOT IN ('MANUAL','ASSISTED_MANUAL','LOCAL_OCR')""",
                    "artifact evaluation character relation": """SELECT COUNT(*) FROM artifact_evaluations e
                        WHERE NOT EXISTS (SELECT 1 FROM snapshots s JOIN snapshot_characters c
                        ON c.snapshot_id=s.id WHERE s.account_id=e.account_id AND c.character_key=e.character_key)""",
                }
                if "artifact_evaluations" not in tables:
                    checks.pop("artifact evaluation status")
                invalid_rows = {
                    name: connection.execute(query).fetchone()[0]
                    for name, query in checks.items()
                }
                invalid_rows = {name: count for name, count in invalid_rows.items() if count}
                if invalid_rows:
                    raise BackupError(
                        "BACKUP_DATABASE_LOGIC_INVALID",
                        "Database contains values or relations outside the supported domain.",
                        {"invalidRows": invalid_rows},
                    )
            finally:
                connection.close()

            if schema not in {None, *SUPPORTED_DB_SCHEMAS}:
                raise BackupError(
                    "BACKUP_SCHEMA_INCOMPATIBLE",
                    "Database schema is not compatible with this app version.",
                    {"databaseSchemaVersion": schema},
                )
            if schema == DB_SCHEMA_HEAD and "account_planning_intents" not in tables:
                raise BackupError("BACKUP_SCHEMA_INCOMPATIBLE",
                                  "Database is missing build intent configuration.")
            return DatabaseValidation(schema, tuple(sorted(tables)))
        except BackupError:
            raise
        except Exception as exc:
            raise BackupError(
                "BACKUP_DATABASE_INVALID",
                "Could not validate the SQLite database.",
                {"reason": str(exc)},
            ) from exc

    def export_copy(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def prepare_restore(self, staged_db: Path, staged_snapshots: Path, expected_snapshot_count: int) -> str | None:
        state = self.validate(staged_db)
        snapshot_files = [path for path in staged_snapshots.rglob("*") if path.is_file()]
        if len(snapshot_files) != expected_snapshot_count:
            raise BackupError(
                "BACKUP_SNAPSHOT_FILES_MISMATCH", "Snapshot files do not match the manifest.")

        connection = sqlite3.connect(staged_db)
        try:
            rows = connection.execute("SELECT id, raw_path FROM snapshots").fetchall()
            for snapshot_id, old_path in rows:
                old_file = Path(old_path) if old_path else None
                try:
                    relative = old_file.relative_to(self.snapshot_dir) if old_file else None
                except ValueError:
                    relative = Path(old_file.name) if old_file else None
                restored = staged_snapshots / relative if relative else None
                if not restored or not restored.is_file():
                    raise BackupError(
                        "BACKUP_SNAPSHOT_MISSING",
                        "A GOOD snapshot file referenced by the database is missing.",
                        {"snapshotId": snapshot_id},
                    )
                connection.execute(
                    "UPDATE snapshots SET raw_path=? WHERE id=?",
                    (str(self.snapshot_dir / relative), snapshot_id),
                )
            connection.commit()
        finally:
            connection.close()

        if len(snapshot_files) != len(rows):
            raise BackupError(
                "BACKUP_SNAPSHOT_FILES_MISMATCH",
                "Backup contains unreferenced or missing snapshot files.",
            )
        return state.schema

    def install(self, staged_db: Path, rollback_path: Path) -> bool:
        """Install the staged DB, returning whether a previous live DB existed."""
        self.database.parent.mkdir(parents=True, exist_ok=True)
        existed = self.database.exists()
        if existed:
            live_copy = sqlite3.connect(self.database)
            rollback_copy = sqlite3.connect(rollback_path)
            try:
                live_copy.backup(rollback_copy)
            finally:
                rollback_copy.close()
                live_copy.close()
            target = sqlite3.connect(self.database)
            source = sqlite3.connect(staged_db)
            try:
                source.backup(target)
            finally:
                source.close()
                target.close()
        else:
            os.replace(staged_db, self.database)
        return existed

    def rollback(self, rollback_path: Path | None, *, existed_before: bool, installed: bool) -> None:
        if not installed:
            return
        if existed_before and rollback_path and rollback_path.exists():
            restored = sqlite3.connect(rollback_path)
            live = sqlite3.connect(self.database)
            try:
                restored.backup(live)
            finally:
                live.close()
                restored.close()
        elif self.database.exists():
            self.database.unlink()
