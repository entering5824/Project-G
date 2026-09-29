"""Port for the account facts needed to evaluate GameData coverage."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AccountCatalogFacts:
    character_keys: tuple[str, ...] = ()
    equipped_weapon_keys: tuple[str, ...] = ()


class GameDataAccountGateway(Protocol):
    def load_catalog_facts(self) -> AccountCatalogFacts: ...
