"""Persisted facts required to compose the desktop overview."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class OverviewCharacterFact:
    key: str
    level: int
    ascension: int
    talents: dict[str, int]
    weapon: dict[str, Any] | None
    artifacts: tuple[dict[str, Any], ...]
    tier_score: float | int | None
    build_profiles: tuple[dict[str, Any], ...]
    knowledge_coverage: dict[str, Any]
    teams: tuple[dict[str, Any], ...]
    priority_override: str = "NORMAL"
    element: str | None = None
    constellation: int = 0


@dataclass(frozen=True)
class OverviewContext:
    snapshot_id: str | None
    today: dict[str, Any] | None = None
    roadmap: dict[str, Any] | None = None
    characters: tuple[OverviewCharacterFact, ...] = ()
    personal_priorities: dict[str, str] | None = None
    theater_config: dict[str, Any] | None = None
    snapshot_imported_at: datetime | None = None


@dataclass(frozen=True)
class OverviewData:
    values: dict[str, Any]


class OverviewGateway(Protocol):
    def load_context(self) -> OverviewContext: ...
