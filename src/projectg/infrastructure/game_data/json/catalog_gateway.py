"""Configured local GameData adapter."""

from projectg.domain.game_catalog.models import GameData
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.game_data.json.repository import get_game_data


class LocalGameDataGateway:
    def __init__(self, configuration: Settings):
        self._configuration = configuration

    def load(self) -> GameData:
        return get_game_data(self._configuration)
