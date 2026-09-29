"""SQLite target persistence primitives used by the TargetGateway adapter."""

from projectg.infrastructure.persistence.sqlite.targets.context_reader import TargetContextReader
from projectg.infrastructure.persistence.sqlite.targets.idempotency_repository import TargetIdempotencyRepository
from projectg.infrastructure.persistence.sqlite.targets.preset_repository import (
    PresetActivation,
    PresetActivationPlan,
    PresetCreation,
    TargetPresetRepository,
)
from projectg.infrastructure.persistence.sqlite.targets.target_writer import TargetWriteBatch, TargetWriter

__all__ = [
    "PresetActivation",
    "PresetActivationPlan",
    "PresetCreation",
    "TargetContextReader",
    "TargetIdempotencyRepository",
    "TargetPresetRepository",
    "TargetWriteBatch",
    "TargetWriter",
]
