"""Validate and save one character's planner configuration."""

from dataclasses import dataclass

from projectg.application.ports.outbound.character_configuration_gateway import (
    CharacterConfigurationData,
    CharacterConfigurationGateway,
)
from projectg.domain.planning.character_configuration import validate_character_configuration


@dataclass(frozen=True)
class SaveCharacterConfigurationRequest:
    character_key: str
    tier_key: str | None
    priority_override: str


class SaveCharacterConfiguration:
    def __init__(self, gateway: CharacterConfigurationGateway):
        self._gateway = gateway

    def execute(self, request: SaveCharacterConfigurationRequest) -> CharacterConfigurationData:
        context = self._gateway.load_context(request.character_key)
        validate_character_configuration(
            owned=context.owned,
            tiers=context.data.tiers,
            tier_key=request.tier_key,
            priority_override=request.priority_override,
        )
        if (
            context.data.tier_key == request.tier_key
            and context.data.priority_override == request.priority_override
        ):
            return context.data
        return self._gateway.commit_validated(
            request.character_key,
            tier_key=request.tier_key,
            priority_override=request.priority_override,
        )
