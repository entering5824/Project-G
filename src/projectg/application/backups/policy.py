"""Backup-format compatibility and retention policy.

This module intentionally contains no filesystem, ZIP, or SQLite calls. Outer
adapters supply metadata; the application policy decides whether that metadata
belongs to a supported ProjectG backup and which recovery points should remain.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone

from projectg.application.backups.errors import BackupError
from projectg.application.backups.models import (
    AutomaticBackupCandidate,
    BackupFileIntegrity,
    BackupManifest,
)

BACKUP_SCHEMA_VERSION = 2
DB_SCHEMA_HEAD = "0019_build_intents"
SUPPORTED_DB_SCHEMAS = frozenset({
    "0007_snapshot_path_relocation",
    "0008_snapshot_reference_foreign_keys",
    "0009_target_import_idempotency",
    "0010_snapshot_coverage_artifact_rv",
    "0011_target_presets",
    "0012_inventory_reserves",
    "0013_plan_runs_today_state",
    "0014_planner_teams",
    "0015_account_availability_settings",
    "0016_primary_planner_team",
    "0017_remove_inventory",
    "0018_tier_pack",
    DB_SCHEMA_HEAD,
})


def parse_backup_manifest(raw: Mapping[str, object]) -> BackupManifest:
    if not isinstance(raw, Mapping):
        raise BackupError("BACKUP_INVALID_MANIFEST", "Backup manifest must be an object.")

    backup_version = raw.get("backupSchemaVersion")
    if backup_version not in {1, BACKUP_SCHEMA_VERSION}:
        raise BackupError(
            "BACKUP_SCHEMA_INCOMPATIBLE",
            "Backup format version is not supported.",
            {"backupSchemaVersion": backup_version},
        )

    database_schema = raw.get("databaseSchemaVersion")
    if database_schema not in {*SUPPORTED_DB_SCHEMAS, "metadata-only"}:
        raise BackupError(
            "BACKUP_SCHEMA_INCOMPATIBLE",
            "Database schema version is not supported.",
            {"databaseSchemaVersion": database_schema},
        )

    def _integer(name: str, *, default: int = 0) -> int:
        value = raw.get(name, default)
        if type(value) is not int or value < 0:
            raise BackupError(
                "BACKUP_INVALID_MANIFEST", f"Backup manifest field {name} is invalid.")
        return value

    files_raw = raw.get("files", {})
    files: dict[str, BackupFileIntegrity] = {}
    if backup_version >= 2:
        if not isinstance(files_raw, Mapping):
            raise BackupError(
                "BACKUP_INTEGRITY_MANIFEST_INVALID",
                "File integrity manifest is invalid.",
            )
        for path, entry in files_raw.items():
            if not isinstance(path, str) or not isinstance(entry, Mapping):
                raise BackupError(
                    "BACKUP_INTEGRITY_MANIFEST_INVALID",
                    "File integrity entry is malformed.",
                )
            size = entry.get("sizeBytes")
            digest = entry.get("sha256")
            if (
                type(size) is not int
                or size < 0
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest.lower())
            ):
                raise BackupError(
                    "BACKUP_INTEGRITY_MANIFEST_INVALID",
                    "File integrity entry is malformed.",
                    {"path": path},
                )
            files[path] = BackupFileIntegrity(digest.lower(), size)

    exported_at = raw.get("exportedAt")
    reason = raw.get("reason")
    app_version = raw.get("appVersion")
    if not isinstance(exported_at, str) or not isinstance(reason, str) or not isinstance(app_version, str):
        raise BackupError("BACKUP_INVALID_MANIFEST", "Backup manifest metadata is invalid.")

    return BackupManifest(
        backup_schema_version=int(backup_version),
        app_version=app_version,
        database_schema_version=str(database_schema),
        exported_at=exported_at,
        reason=reason,
        includes_akasha_images=bool(raw.get("includesAkashaImages", False)),
        snapshot_file_count=_integer("snapshotFileCount"),
        akasha_file_count=_integer("akashaFileCount"),
        files=files,
    )


def select_automatic_backups_to_keep(
    candidates: Iterable[AutomaticBackupCandidate],
    *,
    keep_last: int = 20,
    keep_daily: int = 7,
    keep_weekly: int = 4,
) -> frozenset[str]:
    """Return the recovery-point paths retained by rolling/day/week policy."""

    ordered = sorted(candidates, key=lambda item: (item.modified_at, item.path), reverse=True)
    retained = {item.path for item in ordered[: max(1, keep_last)]}
    daily: dict[object, str] = {}
    weekly: dict[tuple[int, int], str] = {}
    for item in ordered:
        created = datetime.fromtimestamp(item.modified_at, timezone.utc)
        daily.setdefault(created.date(), item.path)
        iso = created.isocalendar()
        weekly.setdefault((iso.year, iso.week), item.path)
    retained.update(list(daily.values())[: max(0, keep_daily)])
    retained.update(list(weekly.values())[: max(0, keep_weekly)])
    return frozenset(retained)
