"""Set or clear the account's Today pin."""

from dataclasses import dataclass

from projectg.application.ports.outbound.planner_state_gateway import PinState, PlannerStateGateway


@dataclass(frozen=True)
class SetPinRequest:
    character_key: str | None


class SetPin:
    def __init__(self, gateway: PlannerStateGateway):
        self._gateway = gateway

    def execute(self, request: SetPinRequest) -> PinState:
        if request.character_key is not None and not self._gateway.owns_character(request.character_key):
            raise ValueError("Character is not owned in the current snapshot.")
        return self._gateway.persist_pin(request.character_key)
