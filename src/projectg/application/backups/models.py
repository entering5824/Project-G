"""Typed backup boundary models shared by use cases and outer adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class BackupFileIntegrity:
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class BackupManifest:
    backup_schema_version: int
    app_version: str
    database_schema_version: str
    exported_at: str
    reason: str
    includes_akasha_images: bool
    snapshot_file_count: int
    akasha_file_count: int
    files: Mapping[str, BackupFileIntegrity]

    def to_mapping(self) -> dict:
        return {
            "backupSchemaVersion": self.backup_schema_version,
            "appVersion": self.app_version,
            "databaseSchemaVersion": self.database_schema_version,
            "exportedAt": self.exported_at,
            "reason": self.reason,
            "includesAkashaImages": self.includes_akasha_images,
            "snapshotFileCount": self.snapshot_file_count,
            "akashaFileCount": self.akasha_file_count,
            "files": {
                path: {"sha256": value.sha256, "sizeBytes": value.size_bytes}
                for path, value in self.files.items()
            },
        }


@dataclass(frozen=True)
class AutomaticBackupCandidate:
    path: str
    modified_at: float


@dataclass(frozen=True)
class BackupExportResult:
    path: str
    manifest: BackupManifest


@dataclass(frozen=True)
class BackupRestoreResult:
    manifest: BackupManifest
    pre_restore_backup: str | None
