"""Filesystem-facing port for validated local GameData packs."""

from dataclasses import dataclass
from typing import Protocol

from projectg.domain.game_catalog.models import GameData


@dataclass(frozen=True)
class GameDataPackDocument:
    path: str
    data: GameData


@dataclass(frozen=True)
class GameDataInstallReceipt:
    path: str
    backup_path: str | None


class GameDataPackStorage(Protocol):
    def load_installed(self) -> GameDataPackDocument: ...

    def load_candidate(self, path: str) -> GameDataPackDocument: ...

    def install_candidate(self, path: str) -> GameDataInstallReceipt: ...

    def export_installed(self, destination: str) -> str: ...
