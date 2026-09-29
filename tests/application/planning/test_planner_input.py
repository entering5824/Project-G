from datetime import datetime, timezone

from projectg.application.planning.input import prepare_planner_input
from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack
from projectg.application.ports.outbound.planner_gateway import (
    PlannerArtifactEvaluationFact,
    PlannerCharacterFact,
    PlannerFacts,
    PlannerArtifactFact,
    PlannerTeamFact,
    PlannerTierPackFact,
)
from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.domain.game_catalog.models import ArtifactSetDefinition, DomainDefinition, GameData
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG


def _pack() -> BuildKnowledgePack:
    progression = {
        "level": 90,
        "ascension": 6,
        "levelImportance": 0.8,
        "talents": {
            "normal": {"enabled": True, "target": 9, "importance": 0.6},
            "skill": {"enabled": True, "target": 10, "importance": 0.9},
            "burst": {"enabled": True, "target": 10, "importance": 0.9},
        },
        "weapon": {"targetLevel": 90, "importance": 0.8},
    }
    profile = {
        "id": "main",
        "status": "VERIFIED",
        "progression": progression,
        "artifacts": {},
    }
    return BuildKnowledgePack(
        "test-pack",
        "7.1",
        {"Amber": [profile]},
        (),
        {
            "missing": [],
            "recommendationsReady": True,
            "advancedCoverageReady": False,
        },
    )


def _game() -> GameData:
    return GameData(
        metadata={"data_version": "test"},
        domains={
            "artifact-domain": DomainDefinition(
                key="artifact-domain",
                type="ARTIFACT",
                reward_material_families=(),
                name="Artifact Domain",
            )
        },
        artifact_sets={
            "SetA": ArtifactSetDefinition(
                key="SetA", name="Set A", domain_key="artifact-domain"
            )
        },
    )


def test_prepare_planner_input_handles_missing_snapshot_without_build_pack():
    prepared = prepare_planner_input(
        PlannerFacts(has_snapshot=False),
        _game(),
        None,
        DEFAULT_PLANNER_CONFIG,
    )

    assert prepared.value.characters == {}
    assert prepared.value.artifact_domains["SetA"]["key"] == "artifact-domain"
    assert [issue["code"] for issue in prepared.issues] == ["INVALID_ACCOUNT_STATE"]


def test_prepare_planner_input_owns_tier_team_and_artifact_freshness_policy():
    facts = PlannerFacts(
        has_snapshot=True,
        characters=(PlannerCharacterFact(
            key="Amber",
            level=80,
            ascension=5,
            talents={"auto": 8, "skill": 8, "burst": 8},
            constellation=1,
            artifact_fingerprint="new-fingerprint",
            artifacts={"flower": PlannerArtifactFact("SetA", None, None, 20, None)},
        ),),
        teams=(PlannerTeamFact(("Amber",), True),),
        artifact_evaluations=(PlannerArtifactEvaluationFact(
            id="eval-1",
            character_key="Amber",
            imported_at=datetime(2026, 9, 26, tzinfo=timezone.utc),
            source="MANUAL",
            status="CONFIRMED",
            raw_metrics={"rv": 600},
            normalized_metrics={},
            parser_confidence=1.0,
            artifact_fingerprint="old-fingerprint",
        ),),
        artifact_quality_config=ArtifactQualityConfig(),
        tier_pack=PlannerTierPackFact(
            scores={"Amber": 90},
            controls={"Amber": "FORCE_INCLUDE"},
            minimum_tier_for_roadmap="B",
            selected_sets={"Amber": "SetA"},
        ),
    )

    prepared = prepare_planner_input(facts, _game(), _pack(), DEFAULT_PLANNER_CONFIG)
    inp = prepared.value

    assert inp.character_targets["Amber"]["level"] == 90
    assert inp.tiers["score:90"].label == "S+"
    assert inp.tier_assignments == {"Amber": "score:90"}
    assert inp.saved_team_members == {"Amber"}
    assert inp.primary_team_members == {"Amber"}
    assert inp.minimum_tier_score == 34
    assert inp.selected_sets == {"Amber": "SetA"}
    assert inp.artifact_evaluations["Amber"]["stale"] is True
    assert inp.artifact_evaluations["Amber"]["freshnessStatus"] == "POSSIBLY_STALE"
    assert any(issue["code"] == "BUILD_KNOWLEDGE_DEPTH" for issue in prepared.issues)


def test_saved_priority_reaches_goal_scoring():
    from dataclasses import replace
    from projectg.domain.planning.engine import PlannerEngine

    facts = PlannerFacts(
        has_snapshot=True,
        characters=(PlannerCharacterFact("Amber", 40, 2,
                    {"auto": 1, "skill": 1, "burst": 1}, 0),),
        tier_pack=PlannerTierPackFact({"Amber": 70}, {}, "B", {}),
    )
    normal = prepare_planner_input(facts, _game(), _pack(), DEFAULT_PLANNER_CONFIG).value
    prioritized = prepare_planner_input(replace(facts, priority_overrides={"Amber": "PRIORITIZED"}),
                                       _game(), _pack(), DEFAULT_PLANNER_CONFIG).value
    normal_goals = {g.goal_key: g for g in PlannerEngine().run(normal, generated_at="2026-09-27T00:00:00Z").global_plan}
    priority_goals = PlannerEngine().run(prioritized, generated_at="2026-09-27T00:00:00Z").global_plan
    assert priority_goals
    assert all(g.priority_mode == "PRIORITIZED" for g in priority_goals)
    assert any(g.final_score > normal_goals[g.goal_key].final_score for g in priority_goals)
