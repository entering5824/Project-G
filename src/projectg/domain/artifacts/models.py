from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EvaluationSource(StrEnum):
    MANUAL = "MANUAL"
    ASSISTED_MANUAL = "ASSISTED_MANUAL"
    LOCAL_OCR = "LOCAL_OCR"


class EvaluationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class QualityStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    NEEDS_QUALITY_CONFIG = "NEEDS_QUALITY_CONFIG"
    BELOW_TARGET = "BELOW_TARGET"
    COMPLETE = "COMPLETE"
    INVALID_DATA = "INVALID_DATA"


QUALITY_LABELS = ("POOR", "ACCEPTABLE", "GOOD", "EXCELLENT")
TARGET_LABEL_SCORE = {"POOR": 0.0, "ACCEPTABLE": 1 / 3, "GOOD": 2 / 3, "EXCELLENT": 1.0}


@dataclass(frozen=True)
class ArtifactQualityConfig:
    version: int = 0
    adapter_type: str = "rv"
    thresholds: dict[str, float | None] = field(default_factory=lambda: {key: None for key in QUALITY_LABELS})

    @property
    def configured(self) -> bool:
        values = [self.thresholds.get(key) for key in QUALITY_LABELS]
        return all(value is not None for value in values)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "adapterType": self.adapter_type,
                "thresholds": dict(self.thresholds)}


@dataclass(frozen=True)
class ArtifactQualityResult:
    status: QualityStatus
    normalized_score: float | None
    quality_label: str | None
    target_score: float | None
    deficiency: float | None
    weak_slots: list[str] = field(default_factory=list)
    metric_key: str | None = None
    stale: bool = False
    developer_input: bool = False
    message: str | None = None
