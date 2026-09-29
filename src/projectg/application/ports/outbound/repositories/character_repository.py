"""Persistence contract for observed character state."""

from typing import Protocol

from projectg.domain.planning.models import CharacterState


class CharacterRepository(Protocol):
    def get(self, character_key: str) -> CharacterState | None: ...

    def save(self, character: CharacterState) -> None: ...
