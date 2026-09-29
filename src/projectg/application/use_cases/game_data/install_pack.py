"""Install a validated GameData pack through atomic local storage."""

from projectg.application.game_data.models import GameDataPackResult
from projectg.application.game_data.policy import build_pack_result
from projectg.application.ports.outbound.game_data_account_gateway import GameDataAccountGateway
from projectg.application.ports.outbound.game_data_pack_storage import GameDataPackStorage
from projectg.application.use_cases.game_data.requests import GameDataPathRequest


class InstallGameDataPack:
    def __init__(self, storage: GameDataPackStorage, account_gateway: GameDataAccountGateway):
        self._storage = storage
        self._account_gateway = account_gateway

    def execute(self, request: GameDataPathRequest) -> GameDataPackResult:
        # Parse and validate before storage is allowed to mutate the installed pack.
        self._storage.load_candidate(request.path)
        receipt = self._storage.install_candidate(request.path)
        installed = self._storage.load_installed()
        facts = self._account_gateway.load_catalog_facts()
        return build_pack_result(installed, facts, backup_path=receipt.backup_path)
