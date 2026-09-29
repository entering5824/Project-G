"""Restore account data from a selected backup."""

from dataclasses import dataclass

from projectg.application.ports.outbound.backup_gateway import BackupGateway
from projectg.application.ports.outbound.support_gateway import SupportData


@dataclass(frozen=True)
class RestoreBackupRequest:
    source: str


class RestoreBackup:
    def __init__(self, gateway: BackupGateway):
        self._gateway = gateway

    def execute(self, request: RestoreBackupRequest) -> SupportData:
        result = self._gateway.restore(request.source)
        return SupportData({
            "restored": True,
            "manifest": result.manifest.to_mapping(),
            "preRestoreBackup": result.pre_restore_backup,
        })
