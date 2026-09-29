"""Validate and preview a candidate GameData pack without installing it."""

from projectg.application.game_data.models import GameDataPackResult
from projectg.application.game_data.policy import build_pack_result
from projectg.application.ports.outbound.game_data_account_gateway import GameDataAccountGateway
from projectg.application.ports.outbound.game_data_pack_storage import GameDataPackStorage
from projectg.application.use_cases.game_data.requests import GameDataPathRequest


class PreviewGameDataPack:
    def __init__(self, storage: GameDataPackStorage, account_gateway: GameDataAccountGateway):
        self._storage = storage
        self._account_gateway = account_gateway

    def execute(self, request: GameDataPathRequest) -> GameDataPackResult:
        candidate = self._storage.load_candidate(request.path)
        current_document = self._storage.load_installed()
        facts = self._account_gateway.load_catalog_facts()
        current = build_pack_result(current_document, facts)
        return build_pack_result(candidate, facts, current=current)
