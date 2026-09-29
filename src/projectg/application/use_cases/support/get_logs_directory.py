"""Expose the active local log directory to the desktop boundary."""

from projectg.application.ports.outbound.support_gateway import LogDirectory, SupportGateway


class GetLogsDirectory:
    def __init__(self, gateway: SupportGateway):
        self._gateway = gateway

    def execute(self) -> LogDirectory:
        return self._gateway.logs_directory()
