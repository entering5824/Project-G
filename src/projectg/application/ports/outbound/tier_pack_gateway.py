"""Ports for persisted tier-pack facts and validated writes."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TierPackData:
    values: dict[str, Any]


@dataclass(frozen=True)
class TierPackContext:
    pack: dict[str, Any]
    pack_hash: str
    owned_characters: frozenset[str]
    character_keys: frozenset[str]
    artifact_set_keys: frozenset[str]
    set_options: dict[str, tuple[str, ...]]


class TierPackGateway(Protocol):
    def load_context(self) -> TierPackContext: ...

    def commit_validated(self, payload: dict[str, Any]) -> dict[str, Any]: ...
