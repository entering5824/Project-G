"""Validate and save planner, artifact, and account settings."""

from dataclasses import dataclass
from typing import Any

from projectg.application.ports.outbound.settings_gateway import SettingsData, SettingsGateway
from projectg.domain.account.settings import normalize_account_settings
from projectg.domain.artifacts.validation import validate_quality_config
from projectg.domain.planning.config import config_from_payload, config_payload


@dataclass(frozen=True)
class SaveSettingsRequest:
    planner: dict[str, Any]
    artifact: dict[str, Any]
    account: dict[str, Any] | None = None


class SaveSettings:
    def __init__(self, gateway: SettingsGateway):
        self._gateway = gateway

    def execute(self, request: SaveSettingsRequest) -> SettingsData:
        planner = config_payload(config_from_payload(request.planner, version="validated"))
        artifact_config = validate_quality_config(request.artifact)
        artifact = {
            "adapterType": artifact_config.adapter_type,
            "thresholds": artifact_config.thresholds,
        }
        account = (
            normalize_account_settings(request.account)
            if request.account is not None
            else None
        )
        return self._gateway.commit_validated(planner, artifact, account)
