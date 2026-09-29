"""Read current application settings."""

from projectg.application.ports.outbound.settings_gateway import SettingsData, SettingsGateway


class GetSettings:
    def __init__(self, gateway: SettingsGateway):
        self._gateway = gateway

    def execute(self) -> SettingsData:
        return self._gateway.load()
