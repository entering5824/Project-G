"""Backup archive driver port."""

from typing import Protocol

from projectg.application.backups.models import BackupExportResult, BackupRestoreResult


class BackupGateway(Protocol):
    def create_manual(self, destination: str) -> BackupExportResult: ...

    def restore(self, source: str) -> BackupRestoreResult: ...
