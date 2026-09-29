"""Translate team use cases to the desktop payload contract."""

from typing import Any

from projectg.application.use_cases.teams.get_teams import GetTeams
from projectg.application.use_cases.teams.save_teams import SaveTeams, SaveTeamsRequest


class TeamsController:
    def __init__(self, get_teams: GetTeams, save_teams: SaveTeams):
        self._get_teams = get_teams
        self._save_teams = save_teams

    def load(self) -> dict[str, Any]:
        return _payload(self._get_teams.execute())

    def save(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _payload(self._save_teams.execute(SaveTeamsRequest(tuple(rows))))


def _payload(value) -> dict[str, Any]:
    return {
        "ownedCharacters": list(value.owned_characters),
        "importedTeams": list(value.imported_teams),
        "configuredTeams": list(value.configured_teams),
    }
