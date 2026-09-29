"""Support facts and driver operations required by the desktop app."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SupportData:
    values: dict[str, Any]


@dataclass(frozen=True)
class LogDirectory:
    path: str


@dataclass(frozen=True)
class HistorySnapshotFact:
    id: str
    when: str
    current: bool
    previous_snapshot_id: str | None
    snapshot_index: int


@dataclass(frozen=True)
class HistoryEventFact:
    id: str
    when: str
    source: str
    event: str
    character: str | None
    snapshot_id: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class HistoryContext:
    snapshots: tuple[HistorySnapshotFact, ...]
    events: tuple[HistoryEventFact, ...]
    current_snapshot_id: str | None


class SupportGateway(Protocol):
    def load_history(self, limit: int) -> HistoryContext: ...

    def compare_history(self, from_snapshot_id: str, to_snapshot_id: str) -> SupportData: ...


    def logs_directory(self) -> LogDirectory: ...
