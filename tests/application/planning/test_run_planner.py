from datetime import datetime, timezone

from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack
from projectg.application.ports.outbound.planner_gateway import PlannerFacts
from projectg.application.use_cases.planning.run_planner import RunPlanner
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG


class FakePlannerGateway:
    def __init__(self, facts: PlannerFacts):
        self.facts = facts

    def load_config(self):
        return DEFAULT_PLANNER_CONFIG

    def load_facts(self):
        return self.facts


class FakeGameDataGateway:
    def load(self):
        return GameData(metadata={"data_version": "test"})


class FailingBuildKnowledgeGateway:
    def load(self, character_keys: set[str]):
        raise AssertionError("build knowledge must not be loaded without a snapshot")


class FakeBuildKnowledgeGateway:
    def load(self, character_keys: set[str]):
        return BuildKnowledgePack(
            "test", "7.1", {}, (),
            {"missing": [], "recommendationsReady": True, "advancedCoverageReady": True},
        )


class FixedClock:
    def now(self):
        return datetime(2026, 9, 26, tzinfo=timezone.utc)


def test_run_planner_skips_build_knowledge_when_account_has_no_snapshot():
    run = RunPlanner(
        FakePlannerGateway(PlannerFacts(has_snapshot=False)),
        FakeGameDataGateway(),
        FailingBuildKnowledgeGateway(),
        FixedClock(),
    )

    execution = run.execute(limit=7)

    assert execution.result.generated_at == "2026-09-26T00:00:00Z"
    assert execution.config.horizon == DEFAULT_PLANNER_CONFIG.horizon
    assert execution.result.global_plan == []
    assert any(issue.code == "INVALID_ACCOUNT_STATE" for issue in execution.result.unresolved)


def test_run_planner_uses_candidate_config_without_reaching_persistence_for_policy():
    candidate = DEFAULT_PLANNER_CONFIG
    run = RunPlanner(
        FakePlannerGateway(PlannerFacts(has_snapshot=False)),
        FakeGameDataGateway(),
        FailingBuildKnowledgeGateway(),
        FixedClock(),
    )

    execution = run.execute(candidate_config=candidate)

    assert execution.config is candidate
    assert execution.planner_input.config is candidate
