"""Read the installed GameData pack status."""

from projectg.application.game_data.models import GameDataPackResult
from projectg.application.game_data.policy import build_pack_result
from projectg.application.ports.outbound.game_data_account_gateway import GameDataAccountGateway
from projectg.application.ports.outbound.game_data_pack_storage import GameDataPackStorage


class GetInstalledGameDataStatus:
    def __init__(self, storage: GameDataPackStorage, account_gateway: GameDataAccountGateway):
        self._storage = storage
        self._account_gateway = account_gateway

    def execute(self) -> GameDataPackResult:
        document = self._storage.load_installed()
        facts = self._account_gateway.load_catalog_facts()
        return build_pack_result(document, facts)
