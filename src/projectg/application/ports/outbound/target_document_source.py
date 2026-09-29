"""Boundary for reading and sizing target JSON documents."""

from typing import Protocol


class TargetDocumentSource(Protocol):
    def read(self, path: str) -> object: ...

    def encoded_size(self, payload: object) -> int: ...
