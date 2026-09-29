"""List immutable planner run summaries."""

from dataclasses import dataclass

from projectg.application.ports.outbound.planner_state_gateway import PlanRunSummary, PlannerStateGateway


@dataclass(frozen=True)
class ListPlanRunsRequest:
    limit: int = 50


class ListPlanRuns:
    def __init__(self, gateway: PlannerStateGateway):
        self._gateway = gateway

    def execute(self, request: ListPlanRunsRequest = ListPlanRunsRequest()) -> tuple[PlanRunSummary, ...]:
        return self._gateway.list_runs(request.limit)
