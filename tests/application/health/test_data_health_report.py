from projectg.application.health.report import build_data_health_report
from projectg.domain.planning.models import PlannerResult, UnresolvedIssue


def _result(*issues: UnresolvedIssue) -> PlannerResult:
    return PlannerResult(
        generated_at="2026-01-01T00:00:00Z",
        planner_version="test",
        config_version="1",
        configured_characters=1,
        configured_tiers=1,
        total_characters=1,
        generated_goals=0,
        blocked_goals=0,
        actionable_goals=0,
        global_plan=[],
        unresolved=list(issues),
        tier_fallback=0.5,
    )


def test_report_policy_maps_planner_issues_without_persistence_objects():
    result = _result(
        UnresolvedIssue(
            "TARGET_NOT_CONFIGURED",
            "amber",
            "warning",
            "Target missing",
            {"count": 1},
        )
    )

    report = build_data_health_report(
        planner_result=result,
        artifact_quality_configured=True,
        game_error=None,
        plan_cost={"unresolved": []},
    )

    assert report["status"] == "WARNING"
    issue = next(item for item in report["issues"] if item["code"] == "MISSING_TARGET")
    assert issue["details"]["characters"] == ["amber"]
    assert issue["details"]["plannerMessages"] == ["Target missing"]
    assert issue["decisionImpact"]


def test_report_policy_surfaces_driver_failures_and_catalog_coverage():
    report = build_data_health_report(
        planner_result=None,
        artifact_quality_configured=False,
        game_error=None,
        plan_cost=None,
        missing_character_keys=["missing-character"],
        missing_weapon_keys=["missing-weapon"],
        backend_errors=["planner failed"],
        account_available=True,
    )

    assert report["status"] == "ERROR"
    assert report["counts"] == {"issues": 3, "errors": 1, "warnings": 2, "info": 0}
    assert {item["code"] for item in report["issues"]} == {
        "BACKEND_ERROR",
        "GAME_DATA_CHARACTER_COVERAGE",
        "GAME_DATA_WEAPON_COVERAGE",
    }


def test_data_health_use_case_owns_planner_failure_and_catalog_coverage_workflow():
    from projectg.application.ports.outbound.data_health_gateway import DataHealthFacts
    from projectg.application.use_cases.support.get_data_health import GetDataHealth
    from projectg.domain.game_catalog.models import GameData

    class FactsGateway:
        def load_facts(self):
            return DataHealthFacts(
                account_available=True,
                artifact_quality_configured=False,
                character_keys=("missing-character",),
                equipped_weapon_keys=("missing-weapon",),
            )

    class GameGateway:
        def load(self):
            return GameData(metadata={})

    def failed_planner():
        raise RuntimeError("planner failed")

    report = GetDataHealth(FactsGateway(), failed_planner, GameGateway()).execute().values

    assert report["status"] == "ERROR"
    assert report["counts"] == {"issues": 3, "errors": 1, "warnings": 2, "info": 0}
    assert {item["code"] for item in report["issues"]} == {
        "BACKEND_ERROR",
        "GAME_DATA_CHARACTER_COVERAGE",
        "GAME_DATA_WEAPON_COVERAGE",
    }
