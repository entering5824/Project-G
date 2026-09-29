"""Read and compose the account history timeline."""

from projectg.application.ports.outbound.support_gateway import SupportData, SupportGateway
from projectg.application.support.policy import build_history_view


class GetHistory:
    def __init__(self, gateway: SupportGateway):
        self._gateway = gateway

    def execute(self, limit: int = 100) -> SupportData:
        return build_history_view(self._gateway.load_history(limit), limit)
