"""Stable application errors surfaced by target use cases."""

from dataclasses import dataclass


@dataclass
class TargetOperationError(ValueError):
    code: str
    message: str
    details: dict
    status_code: int = 422

    def __str__(self) -> str:
        return self.message
