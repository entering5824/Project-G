"""Compare two account snapshots."""

from dataclasses import dataclass

from projectg.application.ports.outbound.support_gateway import SupportData, SupportGateway


@dataclass(frozen=True)
class CompareHistoryRequest:
    from_snapshot_id: str
    to_snapshot_id: str


class CompareHistory:
    def __init__(self, gateway: SupportGateway):
        self._gateway = gateway

    def execute(self, request: CompareHistoryRequest) -> SupportData:
        return self._gateway.compare_history(request.from_snapshot_id, request.to_snapshot_id)
