"""Contract for configured and imported team data."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TeamsData:
    owned_characters: tuple[str, ...]
    imported_teams: tuple[dict[str, Any], ...]
    configured_teams: tuple[dict[str, Any], ...]


class TeamsGateway(Protocol):
    def load(self) -> TeamsData: ...

    def commit_validated(self, rows: list[dict[str, Any]]) -> TeamsData: ...
