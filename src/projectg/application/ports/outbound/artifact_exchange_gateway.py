"""Persistence boundary for versioned artifact evaluation exchange."""

from dataclasses import dataclass
from typing import Any, Protocol

from projectg.domain.artifacts.models import ArtifactQualityConfig, ArtifactQualityResult


@dataclass(frozen=True)
class ArtifactCharacterContext:
    character_key: str
    artifact_fingerprint: str | None
    target_quality: str
    target_version: int | None
    existing_evaluation: bool


@dataclass(frozen=True)
class ArtifactExchangeContext:
    snapshot_id: str | None
    owned_character_keys: frozenset[str]
    quality_config: ArtifactQualityConfig
    characters: dict[str, ArtifactCharacterContext]


@dataclass(frozen=True)
class ArtifactExchangePreview:
    snapshot_id: str
    evaluations: tuple[dict[str, Any], ...]
    valid_count: int


@dataclass(frozen=True)
class ArtifactEvaluationDecision:
    character_key: str
    metrics: dict[str, Any]
    manually_corrected: bool
    quality: ArtifactQualityResult
    normalized_metrics: dict[str, Any]
    artifact_fingerprint: str | None
    target_version: int | None


@dataclass(frozen=True)
class ArtifactExchangeCommitCommand:
    expected_snapshot_id: str
    evaluations: tuple[ArtifactEvaluationDecision, ...]


@dataclass(frozen=True)
class ArtifactExchangeCommit:
    evaluations: tuple[dict[str, Any], ...]


class ArtifactExchangeGateway(Protocol):
    def load_context(self) -> ArtifactExchangeContext: ...

    def commit_validated(self, command: ArtifactExchangeCommitCommand) -> ArtifactExchangeCommit: ...
