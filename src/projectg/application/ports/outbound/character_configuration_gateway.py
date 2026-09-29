"""Persistence contract for per-character planner settings."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CharacterConfigurationData:
    character_key: str
    tier_config_version: int
    tiers: tuple[dict[str, Any], ...]
    tier_key: str | None
    tier_assignment_version: int
    priority_override: str
    active_preset_key: str
    presets: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class CharacterConfigurationContext:
    owned: bool
    data: CharacterConfigurationData


class CharacterConfigurationGateway(Protocol):
    def load_context(self, character_key: str) -> CharacterConfigurationContext: ...

    def commit_validated(
        self,
        character_key: str,
        *,
        tier_key: str | None,
        priority_override: str,
    ) -> CharacterConfigurationData: ...
