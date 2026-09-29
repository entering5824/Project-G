"""Translate settings use-case responses into the desktop boundary shape."""

from typing import Any

from projectg.application.use_cases.settings.get_settings import GetSettings
from projectg.application.use_cases.settings.save_settings import SaveSettings, SaveSettingsRequest


class SettingsController:
    def __init__(self, get_settings: GetSettings, save_settings: SaveSettings):
        self._get_settings = get_settings
        self._save_settings = save_settings

    def load(self) -> dict[str, Any]:
        return _payload(self._get_settings.execute())

    def save(self, planner: dict[str, Any], artifact: dict[str, Any],
             account: dict[str, Any] | None = None) -> dict[str, Any]:
        return _payload(self._save_settings.execute(SaveSettingsRequest(planner, artifact, account)))


def _payload(value) -> dict[str, Any]:
    return {
        "planner": value.planner,
        "plannerVersion": value.planner_version,
        "artifact": value.artifact,
        "artifactConfigured": value.artifact_configured,
        "account": value.account,
    }
