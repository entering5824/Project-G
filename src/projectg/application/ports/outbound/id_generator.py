"""Identifier generation contract."""

from typing import Protocol


class IdGenerator(Protocol):
    def next_id(self) -> str:
        """Return a unique identifier for a new domain record."""
