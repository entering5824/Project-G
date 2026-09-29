"""Local backup coordinator implementing the application BackupGateway port.

This adapter coordinates archive/filesystem mechanics with SQLite-specific
backup mechanics. It owns no backup-format policy: manifest compatibility and
retention selection live in application.backups.policy.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from projectg.application.backups.errors import BackupError
from projectg.application.backups.models import (
    AutomaticBackupCandidate,
    BackupExportResult,
    BackupFileIntegrity,
    BackupManifest,
    BackupRestoreResult,
)
from projectg.application.backups.policy import (
    BACKUP_SCHEMA_VERSION,
    DB_SCHEMA_HEAD,
    select_automatic_backups_to_keep,
)
from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.infrastructure.archive.backup_archive import (
    ZipBackupArchive,
    bytes_integrity,
    file_integrity,
)
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.backup_database import SqliteBackupDatabase
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class LocalBackupGateway:
    def __init__(
        self,
        *,
        configuration: Settings,
        clock: Clock,
        id_generator: IdGenerator,
        maintenance_gate: DatabaseMaintenanceGate | None = None,
        database_engine: Engine | None = None,
        archive: ZipBackupArchive | None = None,
        database: SqliteBackupDatabase | None = None,
    ):
        self.configuration = configuration
        self._clock = clock
        self._id_generator = id_generator
        self._maintenance_gate = maintenance_gate
        self._engine = database_engine
        self._archive = archive or ZipBackupArchive()
        self._database = database or SqliteBackupDatabase(
            configuration.database_url, configuration.snapshot_dir)
        self.database_url = configuration.database_url
        self.database = self._database.database
        self.snapshot_dir = Path(configuration.snapshot_dir).resolve()
        self.backup_dir = Path(configuration.backup_dir).resolve()
        self.akasha_dir = Path(configuration.akasha_dir).resolve()

    def before_mutation(self, db: Session, reason: str) -> Path | None:
        """Create at most one automatic checkpoint per SQLAlchemy transaction."""
        bind = db.get_bind()
        if (
            bind.dialect.name != "sqlite"
            or bind.url.render_as_string(hide_password=True) != self.database_url
        ):
            return None
        transaction = db.get_transaction()
        if transaction is not None and db.info.get("prechange_backup_transaction") is transaction:
            return db.info.get("prechange_backup_path")
        result = self.create_automatic_backup(reason)
        path = Path(result.path)
        if transaction is not None:
            db.info["prechange_backup_transaction"] = transaction
            db.info["prechange_backup_path"] = path
        return path

    def create_manual(self, destination: str) -> BackupExportResult:
        context = self._maintenance_gate.session() if self._maintenance_gate else nullcontext()
        with context:
            return self._create_backup(Path(destination), reason="MANUAL_EXPORT")

    def create_automatic_backup(self, reason: str, *, keep_last: int = 20) -> BackupExportResult:
        stamp = self._clock.now().strftime("%Y%m%dT%H%M%S%fZ")
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", reason).strip("_")[:40] or "CHANGE"
        result = self._create_backup(
            self.backup_dir / f"auto_{stamp}_{slug}.zip", reason=reason)
        self._prune_automatic_backups(keep_last=keep_last)
        return result

    def _create_backup(self, destination: Path | None = None, *, reason: str) -> BackupExportResult:
        database_state = self._database.validate()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        if destination is None:
            stamp = self._clock.now().strftime("%Y%m%dT%H%M%SZ")
            destination = self.backup_dir / f"backup_{stamp}.zip"
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_archive = destination.with_name(
            f".{destination.name}.{self._id_generator.next_id().replace('-', '')}.tmp")

        try:
            with tempfile.TemporaryDirectory(prefix="planner-backup-") as temp_name:
                temp = Path(temp_name)
                db_copy = temp / "database.sqlite"
                self._database.export_copy(db_copy)
                timestamp = self._clock.now().isoformat()
                settings_data = {
                    "accountId": self.configuration.account_id,
                    "accountName": self.configuration.account_name,
                    "serverRegion": self.configuration.server_region,
                }
                settings_bytes = json.dumps(
                    settings_data, ensure_ascii=False, indent=2).encode("utf-8")
                snapshot_files = (
                    sorted(path for path in self.snapshot_dir.rglob("*") if path.is_file())
                    if self.snapshot_dir.exists() else []
                )
                akasha_files = (
                    sorted(path for path in self.akasha_dir.rglob("*") if path.is_file())
                    if self.akasha_dir.exists() else []
                )
                files: dict[str, BackupFileIntegrity] = {
                    "database.sqlite": file_integrity(db_copy),
                    "settings.json": bytes_integrity(settings_bytes),
                }
                files.update({
                    f"snapshots/{path.relative_to(self.snapshot_dir).as_posix()}": file_integrity(path)
                    for path in snapshot_files
                })
                files.update({
                    f"akasha/{path.relative_to(self.akasha_dir).as_posix()}": file_integrity(path)
                    for path in akasha_files
                })
                manifest = BackupManifest(
                    backup_schema_version=BACKUP_SCHEMA_VERSION,
                    app_version="0.1.0",
                    database_schema_version=database_state.schema or DB_SCHEMA_HEAD,
                    exported_at=timestamp,
                    reason=reason,
                    includes_akasha_images=bool(akasha_files),
                    snapshot_file_count=len(snapshot_files),
                    akasha_file_count=len(akasha_files),
                    files=files,
                )
                self._archive.write(
                    temporary_archive,
                    database_copy=db_copy,
                    settings_bytes=settings_bytes,
                    manifest=manifest,
                    snapshot_dir=self.snapshot_dir,
                    akasha_dir=self.akasha_dir,
                )
            with temporary_archive.open("rb") as handle:
                self._archive.inspect(handle)
            os.replace(temporary_archive, destination)
        finally:
            temporary_archive.unlink(missing_ok=True)
        return BackupExportResult(str(destination), manifest)

    def _prune_automatic_backups(
        self, *, keep_last: int = 20, keep_daily: int = 7, keep_weekly: int = 4
    ) -> None:
        rolling = list(self.backup_dir.glob("auto_*.zip"))
        candidates = tuple(
            AutomaticBackupCandidate(str(item), item.stat().st_mtime) for item in rolling)
        retained = select_automatic_backups_to_keep(
            candidates,
            keep_last=keep_last,
            keep_daily=keep_daily,
            keep_weekly=keep_weekly,
        )
        for expired in rolling:
            if str(expired) not in retained:
                expired.unlink(missing_ok=True)

    def restore(self, source: str) -> BackupRestoreResult:
        def run() -> BackupRestoreResult:
            if self._engine is not None:
                self._engine.dispose()
            try:
                with Path(source).open("rb") as handle:
                    return self.restore_content(handle)
            finally:
                if self._engine is not None:
                    self._engine.dispose()

        if self._maintenance_gate is None:
            return run()
        with self._maintenance_gate.exclusive():
            return run()

    def restore_content(self, content: bytes | BinaryIO) -> BackupRestoreResult:
        inspection = self._archive.inspect(content)
        manifest = inspection.manifest
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = self._clock.now().strftime("%Y%m%dT%H%M%SZ")
        pre_restore: BackupExportResult | None = None
        if self.database.exists():
            pre_restore = self._create_backup(
                self.backup_dir / f"pre_restore_{stamp}.zip", reason="PRE_RESTORE")

        database_parent = self.database.parent
        database_parent.mkdir(parents=True, exist_ok=True)
        staging = database_parent / f".restore_{self._id_generator.next_id().replace('-', '')}"
        staging.mkdir()
        db_backup: Path | None = None
        snapshot_backup: Path | None = None
        akasha_backup: Path | None = None
        snapshot_stage: Path | None = None
        akasha_stage: Path | None = None
        snapshot_installed = False
        akasha_installed = False
        db_installed = False
        db_existed_before = False

        try:
            if not isinstance(content, bytes) and content.seekable():
                content.seek(0)
            self._archive.extract(content, staging)
            staged_db = staging / "database.sqlite"
            staged_snapshots = staging / "snapshots"
            staged_snapshots.mkdir(exist_ok=True)
            schema = self._database.prepare_restore(
                staged_db, staged_snapshots, manifest.snapshot_file_count)
            if schema and schema != manifest.database_schema_version:
                raise BackupError(
                    "BACKUP_SCHEMA_MISMATCH",
                    "Database schema and manifest do not match.",
                    {"databaseSchemaVersion": schema,
                     "manifestVersion": manifest.database_schema_version},
                )

            staged_akasha = staging / "akasha"
            staged_akasha.mkdir(exist_ok=True)
            akasha_files = [path for path in staged_akasha.rglob("*") if path.is_file()]
            if len(akasha_files) != manifest.akasha_file_count:
                raise BackupError(
                    "BACKUP_AKASHA_FILES_MISMATCH", "Akasha files do not match the manifest.")

            snapshot_stage = self.snapshot_dir.parent / (
                f".restore_snapshots_{self._id_generator.next_id().replace('-', '')}")
            snapshot_stage.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staged_snapshots, snapshot_stage)
            akasha_stage = self.akasha_dir.parent / (
                f".restore_akasha_{self._id_generator.next_id().replace('-', '')}")
            akasha_stage.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staged_akasha, akasha_stage)

            db_backup = database_parent / (
                f".pre_restore_db_{self._id_generator.next_id().replace('-', '')}")
            db_existed_before = self._database.install(staged_db, db_backup)
            db_installed = True

            snapshot_backup = self.snapshot_dir.parent / (
                f".pre_restore_snapshots_{self._id_generator.next_id().replace('-', '')}")
            if self.snapshot_dir.exists():
                os.replace(self.snapshot_dir, snapshot_backup)
            self.snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(snapshot_stage, self.snapshot_dir)
            snapshot_installed = True

            akasha_backup = self.akasha_dir.parent / (
                f".pre_restore_akasha_{self._id_generator.next_id().replace('-', '')}")
            if self.akasha_dir.exists():
                os.replace(self.akasha_dir, akasha_backup)
            self.akasha_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(akasha_stage, self.akasha_dir)
            akasha_installed = True

            self._database.validate()
            if db_backup.exists():
                db_backup.unlink()
            if snapshot_backup.exists():
                shutil.rmtree(snapshot_backup)
            if akasha_backup.exists():
                shutil.rmtree(akasha_backup)
        except Exception:
            if akasha_installed and self.akasha_dir.exists():
                shutil.rmtree(self.akasha_dir)
            if akasha_backup and akasha_backup.exists():
                os.replace(akasha_backup, self.akasha_dir)
            if snapshot_installed and self.snapshot_dir.exists():
                shutil.rmtree(self.snapshot_dir)
            self._database.rollback(
                db_backup, existed_before=db_existed_before, installed=db_installed)
            if db_backup and db_backup.exists():
                db_backup.unlink()
            if snapshot_backup and snapshot_backup.exists():
                if self.snapshot_dir.exists():
                    shutil.rmtree(self.snapshot_dir)
                os.replace(snapshot_backup, self.snapshot_dir)
            raise
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            if snapshot_stage and snapshot_stage.exists():
                shutil.rmtree(snapshot_stage, ignore_errors=True)
            if akasha_stage and akasha_stage.exists():
                shutil.rmtree(akasha_stage, ignore_errors=True)

        return BackupRestoreResult(
            manifest=manifest,
            pre_restore_backup=pre_restore.path if pre_restore else None,
        )
