"""Preview a Today pin change."""

from dataclasses import dataclass

from projectg.application.planner_state.policy import build_pin_preview
from projectg.application.ports.outbound.planner_state_gateway import PinPreview, PlannerStateGateway


@dataclass(frozen=True)
class PreviewPinRequest:
    character_key: str


class PreviewPin:
    def __init__(self, gateway: PlannerStateGateway):
        self._gateway = gateway

    def execute(self, request: PreviewPinRequest) -> PinPreview:
        return build_pin_preview(
            request.character_key,
            self._gateway.load_pin_context(request.character_key),
        )
