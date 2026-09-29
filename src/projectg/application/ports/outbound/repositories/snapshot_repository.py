"""Persistence contract for normalized account snapshots."""

from typing import Protocol

from projectg.domain.account.models import NormalizedGood


class SnapshotRepository(Protocol):
    def get_by_id(self, snapshot_id: str) -> NormalizedGood | None: ...

    def save(self, snapshot_id: str, snapshot: NormalizedGood) -> None: ...
