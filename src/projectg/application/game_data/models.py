"""Application-owned response models for GameData pack workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GameDataPackResult:
    path: str | None
    metadata: dict[str, Any]
    coverage: dict[str, Any]
    account_coverage: dict[str, Any]
    current: GameDataPackResult | None = None
    error: dict[str, Any] | None = None
    backup_path: str | None = None
