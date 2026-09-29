"""Create an account backup at a caller-selected destination."""

from dataclasses import dataclass

from projectg.application.ports.outbound.backup_gateway import BackupGateway
from projectg.application.ports.outbound.support_gateway import SupportData


@dataclass(frozen=True)
class CreateBackupRequest:
    destination: str


class CreateBackup:
    def __init__(self, gateway: BackupGateway):
        self._gateway = gateway

    def execute(self, request: CreateBackupRequest) -> SupportData:
        result = self._gateway.create_manual(request.destination)
        return SupportData({"path": result.path, "exportedAt": result.manifest.exported_at})
