"""Request models for tier-pack changes."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SaveTierPackRequest:
    payload: dict[str, Any]


@dataclass(frozen=True)
class ValidateTierPackRequest:
    payload: dict[str, Any]
