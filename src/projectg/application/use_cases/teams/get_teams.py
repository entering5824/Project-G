"""Read the saved planner team configuration."""

from projectg.application.ports.outbound.teams_gateway import TeamsData, TeamsGateway


class GetTeams:
    def __init__(self, gateway: TeamsGateway):
        self._gateway = gateway

    def execute(self) -> TeamsData:
        return self._gateway.load()
