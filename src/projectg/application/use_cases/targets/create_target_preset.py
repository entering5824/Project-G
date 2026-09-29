"""Create a named target preset for one owned character."""

from dataclasses import dataclass

from projectg.application.ports.outbound.target_gateway import TargetGateway, TargetOperationResult
from projectg.application.targets.errors import TargetOperationError
from projectg.domain.targets.presets import TargetPresetViolation, next_preset_key


@dataclass(frozen=True)
class CreateTargetPresetRequest:
    character_key: str
    label: str


class CreateTargetPreset:
    def __init__(self, gateway: TargetGateway):
        self._gateway = gateway

    def execute(self, request: CreateTargetPresetRequest) -> TargetOperationResult:
        context = self._gateway.preset_context(request.character_key)
        if not context.owned:
            raise TargetOperationError(
                "CHARACTER_NOT_FOUND",
                "Character is not owned in the current account.",
                {"characterKey": request.character_key},
                status_code=404,
            )
        if context.current_target is None or context.current_preset_key is None:
            raise TargetOperationError(
                "TARGET_REQUIRED",
                "Save the character's first target before creating another preset.",
                {"characterKey": request.character_key},
                status_code=409,
            )
        try:
            label, preset_key = next_preset_key(request.label, context.existing_preset_keys)
        except TargetPresetViolation as exc:
            raise TargetOperationError(
                "INVALID_PRESET_LABEL", exc.message, {"field": exc.field}
            ) from exc
        return self._gateway.create_preset(
            character_key=request.character_key,
            preset_key=preset_key,
            label=label,
            cloned_target=context.current_target,
            cloned_from_preset=context.current_preset_key,
        )
