"""Read access to the versioned game catalog."""

from typing import Protocol

from projectg.domain.game_catalog.models import GameData


class GameDataGateway(Protocol):
    def load(self) -> GameData:
        """Load the active catalog or report its validation failure."""
