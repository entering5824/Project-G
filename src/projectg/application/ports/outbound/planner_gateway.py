"""Persisted facts required to prepare planner input."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.domain.planning.config import PlannerConfig


@dataclass(frozen=True)
class PlannerWeaponFact:
    instance_id: str
    key: str
    level: int
    ascension: int


@dataclass(frozen=True)
class PlannerArtifactFact:
    set_key: str
    rv: float | None
    rv_status: str | None
    level: int
    main_stat: str | None


@dataclass(frozen=True)
class PlannerTeamFact:
    members: tuple[str, ...]
    is_primary: bool = False


@dataclass(frozen=True)
class PlannerCharacterFact:
    key: str
    level: int
    ascension: int
    talents: dict[str, int]
    constellation: int
    weapon: PlannerWeaponFact | None = None
    artifact_fingerprint: str | None = None
    artifacts: dict[str, PlannerArtifactFact] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannerSnapshotFact:
    snapshot_id: str | None
    characters: tuple[PlannerCharacterFact, ...] = ()


@dataclass(frozen=True)
class PlannerArtifactEvaluationFact:
    id: str
    character_key: str
    imported_at: datetime
    source: str
    status: str
    raw_metrics: dict[str, Any]
    normalized_metrics: dict[str, Any]
    parser_confidence: float | None
    artifact_fingerprint: str | None


@dataclass(frozen=True)
class PlannerTierPackFact:
    scores: dict[str, int]
    controls: dict[str, str]
    minimum_tier_for_roadmap: str
    selected_sets: dict[str, str]


@dataclass(frozen=True)
class PlannerFacts:
    has_snapshot: bool
    priority_overrides: dict[str, str] = field(default_factory=dict)
    personal_priority_keys: set[str] = field(default_factory=set)
    theater_priority_keys: set[str] = field(default_factory=set)
    personal_priorities: dict[str, str] = field(default_factory=dict)
    theater_config: dict[str, Any] = field(default_factory=dict)
    characters: tuple[PlannerCharacterFact, ...] = ()
    teams: tuple[PlannerTeamFact, ...] = ()
    artifact_evaluations: tuple[PlannerArtifactEvaluationFact, ...] = ()
    artifact_quality_config: ArtifactQualityConfig = field(default_factory=ArtifactQualityConfig)
    tier_pack: PlannerTierPackFact = field(
        default_factory=lambda: PlannerTierPackFact({}, {}, "B", {})
    )


class PlannerGateway(Protocol):
    def load_config(self) -> PlannerConfig: ...

    def load_facts(self) -> PlannerFacts: ...
