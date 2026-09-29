from projectg.infrastructure.game_data.json.build_profiles import load_build_pack
from projectg.application.planning.build_knowledge import derive_profile_targets
from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack
from projectg.infrastructure.game_data.json.loader import DATASET, load_raw
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.domain.planning.gap_detector import detect_goals
from projectg.domain.planning.models import CharacterState, GoalType, PlannerInput
from projectg.infrastructure.configuration.settings import settings


def test_bundled_pack_allows_roadmap_with_full_basic_roster_coverage():
    characters = {row["key"] for row in load_raw(DATASET)["characters"]}
    pack = load_build_pack(settings.build_profiles_path, character_keys=characters)
    assert pack.coverage["characters"] == 127
    assert pack.coverage["verifiedBasic"] == 127
    assert pack.coverage["releaseReady"] is False
    assert pack.coverage["recommendationsReady"] is True
    assert pack.coverage["advancedCoverageReady"] is False
    knowledge = BuildKnowledgePack(pack.version, pack.game_version, pack.profiles, pack.errors, pack.coverage)
    assert len(derive_profile_targets(knowledge)[1]) == 0
    assert len(derive_profile_targets(knowledge)[0]) == 127


def test_verified_profile_hypotheses_merge_to_common_progression():
    row = {"id": "a", "characterKey": "Test", "status": "VERIFIED", "depth": "BASIC",
        "sources": [{"type": "KQM", "url": "https://example.invalid", "checkedGameVersion": "7.1"}],
        "progression": {"level": 90, "ascension": 6,
            "talents": {"normal": {"enabled": True, "target": 9, "importance": .8},
                        "skill": {"enabled": True, "target": 10, "importance": .9},
                        "burst": {"enabled": True, "target": 8, "importance": .7}},
            "weapon": {"targetLevel": 90, "importance": .8}}}
    other = {**row, "id": "b", "progression": {**row["progression"], "talents": {
        **row["progression"]["talents"], "normal": {"enabled": False, "target": 1, "importance": 0},
        "skill": {"enabled": True, "target": 9, "importance": .8}}}}
    targets, unresolved = derive_profile_targets(BuildKnowledgePack("test", "7.1", {"Test": [row, other]}, (),
        {"missing": [], "characters": 1, "verifiedBasic": 1, "verifiedStandard": 0, "verifiedDeep": 0,
         "minimumStandard": 50, "targetDeep": {"minimum": 20, "maximum": 30}, "stale": [], "releaseReady": False}))
    assert not unresolved
    assert targets["Test"]["talents"]["normal"]["enabled"] is False
    assert targets["Test"]["talents"]["skill"]["target"] == 9


def test_artifact_analysis_uses_slot_rv_and_set_bonus_together():
    profile = {"slotRvTargets": {slot: {"stopFarming": 650} for slot in
        ("flower", "plume", "sands", "goblet", "circlet")},
        "setCombinations": [{"combination": [{"setKey": "SetA", "pieces": 4}], "utility": 1.0},
                            {"combination": [{"setKey": "SetA", "pieces": 2}, {"setKey": "SetB", "pieces": 2}], "utility": .92}]}
    target = {"level": 90, "ascension": 6, "importance": {"level": .7, "ascension": .7},
        "talents": {name: {"enabled": False, "target": 1, "importance": 0} for name in
                    ("normal", "skill", "burst")}, "weapon": {"targetLevel": 90, "importance": .7},
        "artifact": {"enabled": False}, "_buildArtifacts": [profile], "_profiles": []}
    artifacts = {"flower": {"setKey": "SetA", "rv": 710},
        "plume": {"setKey": "SetA", "rv": 680}, "sands": {"setKey": "SetA", "rv": 390},
        "goblet": {"setKey": "SetB", "rv": 520}, "circlet": {"setKey": "SetA", "rv": 460}}
    char = CharacterState("Test", 90, 6, {"auto": 1, "skill": 1, "burst": 1}, artifacts=artifacts)
    inp = PlannerInput({"Test": char}, {"Test": target}, {}, {}, {}, set(), DEFAULT_PLANNER_CONFIG)
    goals, _ = detect_goals(inp)
    artifact = next(goal for goal in goals if goal.type == GoalType.ARTIFACT_QUALITY)
    assert artifact.artifact_weak_slots == ["sands", "goblet", "circlet"]
    assert artifact.artifact_recommended_sets == ["SetA"]


def test_artifact_farming_is_suppressed_when_profiles_conflict_on_set():
    shared = {"slotRvTargets": {}, "setCombinations": [
        {"combination": [{"setKey": "SetA", "pieces": 4}], "utility": 1.0}]}
    conflicting = {"slotRvTargets": {}, "setCombinations": [
        {"combination": [{"setKey": "SetB", "pieces": 4}], "utility": 1.0}]}
    target = {"level": 90, "ascension": 6, "importance": {"level": .7, "ascension": .7},
        "talents": {name: {"enabled": False, "target": 1, "importance": 0} for name in
                    ("normal", "skill", "burst")}, "weapon": {"targetLevel": 90, "importance": .7},
        "artifact": {"enabled": False}, "_buildArtifacts": [shared, conflicting], "_profiles": []}
    char = CharacterState("Test", 90, 6, {"auto": 1, "skill": 1, "burst": 1}, artifacts={})
    inp = PlannerInput({"Test": char}, {"Test": target}, {}, {}, {}, set(), DEFAULT_PLANNER_CONFIG)
    goals, issues = detect_goals(inp)
    assert all(goal.type != GoalType.ARTIFACT_QUALITY for goal in goals)
    assert any(issue.code == "ARTIFACT_SET_ARCHETYPE_CONFLICT" for issue in issues)
