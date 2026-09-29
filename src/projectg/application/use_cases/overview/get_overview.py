"""Load and compose the current account overview."""

from projectg.application.overview.policy import build_overview
from projectg.application.ports.outbound.overview_gateway import OverviewData, OverviewGateway


class GetOverview:
    def __init__(self, gateway: OverviewGateway):
        self._gateway = gateway

    def execute(self) -> OverviewData:
        return build_overview(self._gateway.load_context())
