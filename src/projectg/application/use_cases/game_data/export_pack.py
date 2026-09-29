"""Export the installed GameData pack to a destination."""

from projectg.application.game_data.models import GameDataPackResult
from projectg.application.game_data.policy import metadata_view
from projectg.application.ports.outbound.game_data_pack_storage import GameDataPackStorage
from projectg.application.use_cases.game_data.requests import GameDataPathRequest


class ExportGameDataPack:
    def __init__(self, storage: GameDataPackStorage):
        self._storage = storage

    def execute(self, request: GameDataPathRequest) -> GameDataPackResult:
        installed = self._storage.load_installed()
        exported_path = self._storage.export_installed(request.path)
        return GameDataPackResult(
            path=exported_path,
            metadata=metadata_view(installed.data),
            coverage={},
            account_coverage={},
        )
