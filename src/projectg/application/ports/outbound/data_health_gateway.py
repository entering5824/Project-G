"""Persisted facts required by the Data Health application workflow."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DataHealthFacts:
    account_available: bool
    artifact_quality_configured: bool
    character_keys: tuple[str, ...] = ()
    equipped_weapon_keys: tuple[str, ...] = ()


class DataHealthFactsGateway(Protocol):
    def load_facts(self) -> DataHealthFacts: ...
