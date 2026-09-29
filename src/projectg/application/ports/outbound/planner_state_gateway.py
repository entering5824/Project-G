"""Persistence contract for recorded runs and the user's current Today pin."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PlanRunSummary:
    id: str
    created_at: str
    kind: str
    snapshot_id: str | None
    planner_config_version: int | None
    primary_task: dict[str, Any] | None


@dataclass(frozen=True)
class PlanRunReplay:
    plan_run_id: str
    recorded_at: str
    result: dict[str, Any]
    normalized_input: dict[str, Any]
    target_versions: dict[str, Any]
    planner_config_version: int | None
    source_availability: dict[str, Any]
    context: dict[str, Any]
    hysteresis_state: dict[str, Any]
    engine_version: str | None
    game_data_version: str | None
    rv_formula_version: str | None
    switch_threshold: float | None


@dataclass(frozen=True)
class PinContext:
    owned: bool
    today_plan: dict[str, Any]


@dataclass(frozen=True)
class PinPreview:
    character_key: str
    candidate: dict[str, Any] | None
    strategic_task: dict[str, Any] | None
    conflicts: tuple[dict[str, Any], ...]
    requires_confirmation: bool
    status: str


@dataclass(frozen=True)
class PinState:
    pinned_character_key: str | None


class PlannerStateGateway(Protocol):
    def list_runs(self, limit: int) -> tuple[PlanRunSummary, ...]: ...

    def replay_run(self, run_id: str) -> PlanRunReplay: ...

    def load_pin_context(self, character_key: str) -> PinContext: ...

    def owns_character(self, character_key: str) -> bool: ...

    def persist_pin(self, character_key: str | None) -> PinState: ...
