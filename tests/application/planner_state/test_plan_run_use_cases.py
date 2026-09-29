from projectg.application.ports.outbound.planner_state_gateway import PlanRunReplay, PlanRunSummary
from projectg.application.use_cases.planner_state.list_plan_runs import ListPlanRuns, ListPlanRunsRequest
from projectg.application.use_cases.planner_state.replay_plan_run import ReplayPlanRun, ReplayPlanRunRequest


class FakeGateway:
    def __init__(self):
        self.limit = None
        self.run_id = None

    def list_runs(self, limit):
        self.limit = limit
        return (PlanRunSummary("run-1", "now", "TODAY", "snapshot-1", 2, None),)

    def replay_run(self, run_id):
        self.run_id = run_id
        return PlanRunReplay("run-1", "now", {}, {}, {}, 2, {}, {}, {},
                             "engine", "game", "rv", 0.2)

    def preview_pin(self, character_key):
        raise AssertionError("not used")

    def set_pin(self, character_key):
        raise AssertionError("not used")


def test_list_plan_runs_uses_requested_limit():
    gateway = FakeGateway()
    runs = ListPlanRuns(gateway).execute(ListPlanRunsRequest(12))

    assert gateway.limit == 12
    assert runs[0].id == "run-1"


def test_replay_plan_run_queries_immutable_record_by_id():
    gateway = FakeGateway()
    run = ReplayPlanRun(gateway).execute(ReplayPlanRunRequest("run-1"))

    assert gateway.run_id == "run-1"
    assert run.engine_version == "engine"
