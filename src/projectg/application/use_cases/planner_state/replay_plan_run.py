"""Retrieve the recorded decision for one planner run."""

from dataclasses import dataclass

from projectg.application.ports.outbound.planner_state_gateway import PlanRunReplay, PlannerStateGateway


@dataclass(frozen=True)
class ReplayPlanRunRequest:
    run_id: str


class ReplayPlanRun:
    def __init__(self, gateway: PlannerStateGateway):
        self._gateway = gateway

    def execute(self, request: ReplayPlanRunRequest) -> PlanRunReplay:
        return self._gateway.replay_run(request.run_id)
