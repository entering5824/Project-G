"""Translate game-data use cases into the desktop result shape."""

from typing import Any

from projectg.application.use_cases.game_data.export_pack import ExportGameDataPack
from projectg.application.use_cases.game_data.get_installed_status import GetInstalledGameDataStatus
from projectg.application.use_cases.game_data.install_pack import InstallGameDataPack
from projectg.application.use_cases.game_data.preview_pack import PreviewGameDataPack
from projectg.application.use_cases.game_data.requests import GameDataPathRequest


class GameDataController:
    def __init__(self, status: GetInstalledGameDataStatus, preview: PreviewGameDataPack,
                 install: InstallGameDataPack, export: ExportGameDataPack):
        self._status, self._preview = status, preview
        self._install, self._export = install, export

    def status(self) -> dict[str, Any]:
        return _payload(self._status.execute())

    def preview(self, path: str) -> dict[str, Any]:
        return _payload(self._preview.execute(GameDataPathRequest(path)))

    def install(self, path: str) -> dict[str, Any]:
        payload = _payload(self._install.execute(GameDataPathRequest(path)))
        payload.setdefault("backupPath", None)
        return payload

    def export(self, path: str) -> dict[str, Any]:
        return _payload(self._export.execute(GameDataPathRequest(path)))


def _payload(result) -> dict[str, Any]:
    payload = {"path": result.path, "metadata": result.metadata,
               "coverage": result.coverage, "accountCoverage": result.account_coverage}
    if result.current is not None:
        payload["current"] = _payload(result.current)
    if result.error is not None:
        payload["error"] = result.error
    if result.backup_path is not None:
        payload["backupPath"] = result.backup_path
    return payload
