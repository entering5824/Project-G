"""Read one character's planner configuration."""

from projectg.application.ports.outbound.character_configuration_gateway import (
    CharacterConfigurationData,
    CharacterConfigurationGateway,
)


class GetCharacterConfiguration:
    def __init__(self, gateway: CharacterConfigurationGateway):
        self._gateway = gateway

    def execute(self, character_key: str) -> CharacterConfigurationData:
        context = self._gateway.load_context(character_key)
        if not context.owned:
            raise ValueError("Character is not owned in the current snapshot.")
        return context.data
