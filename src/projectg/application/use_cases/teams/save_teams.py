"""Validate and replace the saved planner team configuration."""

from dataclasses import dataclass
from typing import Any

from projectg.application.ports.outbound.teams_gateway import TeamsData, TeamsGateway
from projectg.domain.teams.configuration import normalize_configured_teams


@dataclass(frozen=True)
class SaveTeamsRequest:
    rows: tuple[dict[str, Any], ...]


class SaveTeams:
    def __init__(self, gateway: TeamsGateway):
        self._gateway = gateway

    def execute(self, request: SaveTeamsRequest) -> TeamsData:
        context = self._gateway.load()
        normalized = normalize_configured_teams(
            list(request.rows), owned_characters=context.owned_characters
        )
        if tuple(normalized) == context.configured_teams:
            return context
        return self._gateway.commit_validated(normalized)
