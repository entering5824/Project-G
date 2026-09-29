"""Persistence contract for generated planner runs."""

from typing import Protocol

from projectg.domain.planning.models import PlannerResult


class PlanRepository(Protocol):
    def save(self, run_id: str, result: PlannerResult) -> None: ...

    def get_by_id(self, run_id: str) -> PlannerResult | None: ...
