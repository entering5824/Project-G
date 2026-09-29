"""Activate a saved target preset for one owned character."""

from dataclasses import dataclass

from projectg.application.ports.outbound.target_gateway import TargetGateway, TargetOperationResult
from projectg.application.targets.errors import TargetOperationError


@dataclass(frozen=True)
class ActivateTargetPresetRequest:
    character_key: str
    preset_key: str


class ActivateTargetPreset:
    def __init__(self, gateway: TargetGateway):
        self._gateway = gateway

    def execute(self, request: ActivateTargetPresetRequest) -> TargetOperationResult:
        context = self._gateway.preset_context(request.character_key)
        if not context.owned:
            raise TargetOperationError(
                "CHARACTER_NOT_FOUND",
                "Character is not owned in the current account.",
                {"characterKey": request.character_key},
                status_code=404,
            )
        if request.preset_key not in context.existing_preset_keys:
            raise TargetOperationError(
                "TARGET_PRESET_NOT_FOUND",
                "Target preset was not found.",
                {"characterKey": request.character_key, "presetKey": request.preset_key},
                status_code=404,
            )
        return self._gateway.activate_preset(request.character_key, request.preset_key)
