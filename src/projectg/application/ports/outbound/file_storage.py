"""Opaque byte storage for imports, exports, snapshots, and backups."""

from typing import Protocol


class FileStorage(Protocol):
    def read(self, key: str) -> bytes:
        """Read an object by its application-level key."""

    def write(self, key: str, content: bytes) -> None:
        """Atomically replace an object by its application-level key."""

    def delete(self, key: str) -> None:
        """Remove an object by its application-level key."""
