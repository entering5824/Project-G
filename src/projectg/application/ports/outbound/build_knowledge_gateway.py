"""Read access to reviewed build-knowledge profiles."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class BuildKnowledgePack:
    version: str
    game_version: str
    profiles: dict[str, list[dict[str, Any]]]
    errors: tuple[str, ...]
    coverage: dict[str, Any]


class BuildKnowledgeGateway(Protocol):
    def load(self, character_keys: set[str]) -> BuildKnowledgePack: ...
