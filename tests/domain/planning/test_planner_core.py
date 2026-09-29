from dataclasses import replace

from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.domain.planning.dependencies import actionable_frontier, resolve_dependencies
from projectg.domain.planning.gap_detector import detect_goals
from projectg.domain.planning.models import (CharacterState, GoalStatus, GoalType, PlannerInput,
                                TierValue, UpgradeGoal, WeaponState)
from projectg.domain.planning.progress import (ascension_deficiency, character_level_deficiency,
                                  talent_deficiency, weapon_level_deficiency)
from projectg.domain.planning.scorer import score_goal
from projectg.domain.planning.engine import PlannerEngine


RUN_AT = "2026-09-26T00:00:00Z"

def run_plan(inp):
    return PlannerEngine().run(inp, generated_at=RUN_AT)


def target(*, level=90, ascension=6, talents=None, weapon=90, importance=None):
    talents = talents or {
        "normal":{"enabled":False,"target":1,"importance":0.0},
        "skill":{"enabled":False,"target":1,"importance":0.0},
        "burst":{"enabled":False,"target":1,"importance":0.0},
    }
    return {"level":level,"ascension":ascension,
        "importance":importance or {"level":0.8,"ascension":0.8},"talents":talents,
        "weapon":{"targetLevel":weapon,"importance":0.8}}


def planner_input(chars, targets, *, tiers=None, assignments=None, priorities=None, teams=None):
    return PlannerInput(chars, targets, tiers or {}, assignments or {}, priorities or {},
                        teams or set(), DEFAULT_PLANNER_CONFIG)


def test_milestone_deficiency_distinguishes_level_progress_and_is_clamped():
    config = DEFAULT_PLANNER_CONFIG
    assert character_level_deficiency(20, 90, config) > character_level_deficiency(80, 90, config)
    assert character_level_deficiency(90, 90, config) == 0
    assert character_level_deficiency(95, 90, config) == 0
    assert weapon_level_deficiency(20, 90, config) > weapon_level_deficiency(80, 90, config)
    assert ascension_deficiency(0, 6) == 1
    assert talent_deficiency(9, 10) < talent_deficiency(1, 10)


def test_gap_detector_exact_or_above_target_generates_no_goal():
    char = CharacterState("A",90,6,{"auto":1,"skill":10,"burst":10},WeaponState("w","Sword",90,6))
    goals, _ = detect_goals(planner_input({"A":char},{"A":target()}))
    assert goals == []


def test_disabled_talent_never_generates_goal_and_weapon_gap_does():
    char = CharacterState("A",90,6,{"auto":1,"skill":1,"burst":1},WeaponState("w","Sword",20,1))
    goals, _ = detect_goals(planner_input({"A":char},{"A":target()}))
    assert [goal.type for goal in goals] == [GoalType.WEAPON_LEVEL]
    assert goals[0].current_value == 20 and goals[0].target_value == 90
    assert goals[0].weapon_instance_id == "w" and goals[0].weapon_key == "Sword"
    assert goals[0].current_value == 20 and goals[0].target_value == 90 and goals[0].next_milestone == 40


def test_missing_target_creates_unresolved_issue_without_progression_goal():
    char = CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)
    goals, issues = detect_goals(planner_input({"A":char},{}))
    assert goals == []
    assert any(issue.code == "TARGET_NOT_CONFIGURED" for issue in issues)


def test_missing_equipped_weapon_is_reported_without_crashing():
    char = CharacterState("A",90,6,{"auto":1,"skill":1,"burst":1},None)
    goals, issues = detect_goals(planner_input({"A":char},{"A":target()}))
    assert all(goal.type != GoalType.WEAPON_LEVEL for goal in goals)
    assert any(issue.code == "EQUIPPED_WEAPON_MISSING" for issue in issues)


def test_specific_weapon_mismatch_is_unresolved_and_does_not_upgrade_wrong_weapon():
    char = CharacterState("A", 90, 6, {"auto": 1, "skill": 1, "burst": 1},
                          WeaponState("w", "CurrentSword", 20, 1))
    configured = target()
    configured["weapon"]["weaponKey"] = "TargetSword"

    goals, issues = detect_goals(planner_input({"A": char}, {"A": configured}))

    assert all(goal.type != GoalType.WEAPON_LEVEL for goal in goals)
    mismatch = next(issue for issue in issues if issue.code == "WEAPON_TARGET_MISMATCH")
    assert mismatch.details == {"currentWeaponKey": "CurrentSword", "targetWeaponKey": "TargetSword",
                                "currentLevel": 20, "targetLevel": 90}


def test_talent_at_ascension_six_blocks_until_ascension_then_becomes_actionable():
    char = CharacterState("A",80,5,{"auto":1,"skill":8,"burst":1},None)
    talents = {"normal":{"enabled":False,"target":1,"importance":0.0},
               "skill":{"enabled":True,"target":10,"importance":1.0},
               "burst":{"enabled":False,"target":1,"importance":0.0}}
    inp = planner_input({"A":char},{"A":target(level=90,ascension=6,weapon=1,talents=talents)},
                        tiers={"S":TierValue("S","S",1.0,0)}, assignments={"A":"S"})
    goals, _ = detect_goals(inp)
    goals = resolve_dependencies(goals)
    ascension = next(g for g in goals if g.type == GoalType.CHARACTER_ASCENSION)
    skill = next(g for g in goals if g.type == GoalType.TALENT_SKILL)
    assert ascension.status == GoalStatus.ACTIONABLE
    assert skill.status == GoalStatus.BLOCKED
    assert skill.dependencies == ["A:CHARACTER_ASCENSION"]
    result = run_plan(inp)
    assert result.global_plan[0].type == GoalType.CHARACTER_ASCENSION
    assert next(i for i,g in enumerate(result.global_plan) if g.type == GoalType.TALENT_SKILL) > 0


def test_simulation_advances_level_and_ascension_in_valid_sequence():
    char = CharacterState("A",1,0,{"auto":1,"skill":1,"burst":1},None)
    inp = planner_input({"A":char},{"A":target(weapon=1)},
                        tiers={"S":TierValue("S","S",1.0,0)}, assignments={"A":"S"})
    result = run_plan(inp)
    levels = [g for g in result.global_plan if g.type == GoalType.CHARACTER_LEVEL]
    ascensions = [g for g in result.global_plan if g.type == GoalType.CHARACTER_ASCENSION]
    assert len(levels) == 1 and len(ascensions) == 1
    assert (levels[0].current_value, levels[0].target_value, levels[0].next_milestone) == (1,90,20)
    assert [(step.current, step.target) for step in levels[0].milestone_chain[:2]] == [(1,20),(20,40)]
    assert levels[0].milestone_chain[-1].target == 90
    from projectg.domain.planning.engine import action_to_dict
    projected = action_to_dict(levels[0], 1)
    assert projected["title"] == "Level 1 → 90"
    assert projected["milestoneChain"][:2] == [{"from": 1, "to": 20}, {"from": 20, "to": 40}]
    assert (ascensions[0].current_value, ascensions[0].target_value, ascensions[0].next_milestone) == (0,6,1)
    assert len({g.id for g in result.global_plan}) == len(result.global_plan)
    # Concrete steps are nested inside one semantic component row.
    assert result.global_plan[0].type == GoalType.CHARACTER_LEVEL


def test_scoring_uses_additive_factors_and_relative_precedence():
    inp = planner_input({}, {}, tiers={"T0":TierValue("T0","T0",1.0),"T3":TierValue("T3","T3",0.4)})
    def goal(key, deficiency=0.5, importance=0.5, tier=0.7, priority="NORMAL"):
        return UpgradeGoal(key,key,key,GoalType.TALENT_SKILL,8,10,importance,deficiency,tier,0.5,0.0,
                           priority_override=DEFAULT_PLANNER_CONFIG.priority_multiplier(priority),
                           tier_configured=True,priority_mode=priority)
    assert score_goal(goal("weapon",0.9,0.9),inp).final_score > score_goal(goal("minor",0.11,0.2),inp).final_score
    assert score_goal(goal("hi",importance=0.9),inp).final_score > score_goal(goal("lo",importance=0.2),inp).final_score
    assert score_goal(goal("T0",tier=1.0),inp).final_score > score_goal(goal("T3",tier=0.4),inp).final_score
    prioritized=score_goal(goal("p",priority="PRIORITIZED"),inp).final_score
    normal=score_goal(goal("n"),inp).final_score
    deprioritized=score_goal(goal("d",priority="DEPRIORITIZED"),inp).final_score
    assert prioritized > normal > deprioritized
    assert prioritized <= 100


def test_missing_tier_is_unranked_but_keeps_an_internal_fallback_for_explicit_override():
    char = CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)
    inp = planner_input({"A":char},{"A":target(weapon=1)})
    goals, _ = detect_goals(inp)
    goal = score_goal(goals[0],inp)
    assert goal.tier_value == 0.70 and not goal.tier_configured
    assert "UNRANKED_CHARACTER" in goal.reason_codes


def test_unranked_character_is_not_added_to_global_priority_without_explicit_override():
    char = CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)
    inp = planner_input({"A":char},{"A":target(weapon=1)})

    result = run_plan(inp)

    assert result.global_plan == []
    assert any(issue.code == "TIER_NOT_CONFIGURED" for issue in result.unresolved)


def test_unranked_character_with_enabled_talent_still_stays_out_of_global_plan():
    char = CharacterState("A",1,0,{"auto":1,"skill":1,"burst":1},None)
    talents = {"normal":{"enabled":False,"target":1,"importance":0.0},
               "skill":{"enabled":True,"target":10,"importance":1.0},
               "burst":{"enabled":False,"target":1,"importance":0.0}}
    inp = planner_input({"A":char},{"A":target(weapon=1,talents=talents)})

    result = run_plan(inp)

    assert result.global_plan == []
    assert any(issue.code == "TIER_NOT_CONFIGURED" for issue in result.unresolved)


def test_explicit_priority_override_can_include_unranked_character():
    char = CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)
    inp = planner_input({"A":char},{"A":target(weapon=1)},priorities={"A":"PRIORITIZED"})

    result = run_plan(inp)

    assert result.global_plan
    assert all(not goal.tier_configured for goal in result.global_plan)


def test_same_normalized_state_produces_same_ordered_plan():
    def build():
        chars={"B":CharacterState("B",20,1,{"auto":1,"skill":1,"burst":1},None),
               "A":CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)}
        targets={key:target(weapon=1) for key in chars}
        tiers={"S":TierValue("S","S",1.0,0)}
        return run_plan(planner_input(chars,targets,tiers=tiers,assignments={key:"S" for key in chars}))
    first, second = build(), build()
    assert [(g.goal_key,g.current_value,g.target_value) for g in first.global_plan] == [(g.goal_key,g.current_value,g.target_value) for g in second.global_plan]


def test_plan_selects_highest_value_upgrade_across_characters():
    high = CharacterState("HighTier",90,6,{"auto":1,"skill":8,"burst":1},None)
    low = CharacterState("LowTier",20,1,{"auto":1,"skill":1,"burst":1},None)
    high_target = target(level=90,ascension=6,weapon=1,importance={"level":0.1,"ascension":0.1},
        talents={"normal":{"enabled":False,"target":1,"importance":0.0},
                 "skill":{"enabled":True,"target":10,"importance":0.1},
                 "burst":{"enabled":False,"target":1,"importance":0.0}})
    low_target = target(level=90,ascension=6,weapon=1,importance={"level":1.0,"ascension":1.0})
    tiers={"S":TierValue("S","S",1.0,0),"B":TierValue("B","B",0.2,1)}
    inp=planner_input({"HighTier":high,"LowTier":low},{"HighTier":high_target,"LowTier":low_target},
        tiers=tiers,assignments={"HighTier":"S","LowTier":"B"})

    result=run_plan(inp)

    assert result.global_plan[0].character_key == "LowTier"
    assert result.global_plan[0].type == GoalType.CHARACTER_LEVEL

    inp.priority_overrides["LowTier"]="PRIORITIZED"
    prioritized=run_plan(inp)
    assert prioritized.global_plan[0].character_key == "LowTier"


def test_manual_character_order_does_not_override_upgrade_value():
    a = CharacterState("A",20,1,{"auto":1,"skill":1,"burst":1},None)
    b = CharacterState("B",20,1,{"auto":1,"skill":1,"burst":1},None)
    tiers={"S":TierValue("S","S",1.0,0)}
    targets={"A":target(weapon=1, importance={"level":1.0,"ascension":1.0}),
             "B":target(weapon=1, importance={"level":0.1,"ascension":0.1})}
    config = replace(DEFAULT_PLANNER_CONFIG, manual_order_enabled=False, manual_order=("B","A"))
    inp=PlannerInput({"A":a,"B":b},targets,tiers,{"A":"S","B":"S"},{},set(),config)

    disabled_result=PlannerEngine(config).run(inp, generated_at=RUN_AT)
    assert disabled_result.global_plan[0].character_key == "A"

    config = replace(config, manual_order_enabled=True)
    inp.config = config
    result=PlannerEngine(config).run(inp, generated_at=RUN_AT)

    assert result.global_plan[0].character_key == "A"


def test_manual_order_and_tier_do_not_override_upgrade_value():
    high = CharacterState("High",20,1,{"auto":1,"skill":1,"burst":1},None)
    low = CharacterState("Low",20,1,{"auto":1,"skill":1,"burst":1},None)
    tiers={"S":TierValue("S","S",1.0,0),"B":TierValue("B","B",0.3,1)}
    targets={key:target(weapon=1) for key in ("High","Low")}
    config = replace(DEFAULT_PLANNER_CONFIG, manual_order_enabled=True, manual_order=("Low","High"))
    inp=PlannerInput({"High":high,"Low":low},targets,tiers,{"High":"S","Low":"B"},{},set(),config)

    assert PlannerEngine(config).run(inp, generated_at=RUN_AT).global_plan[0].character_key == "High"
    inp.priority_overrides["Low"] = "PRIORITIZED"
    assert PlannerEngine(config).run(inp, generated_at=RUN_AT).global_plan[0].character_key == "High"


def test_personal_build_priority_precedes_theater_and_normal_groups():
    personal = CharacterState("Vesna", 20, 1, {"auto": 1, "skill": 1, "burst": 1}, None)
    theater = CharacterState("Theater", 80, 5, {"auto": 1, "skill": 1, "burst": 1}, None)
    normal = CharacterState("Normal", 80, 5, {"auto": 1, "skill": 1, "burst": 1}, None)
    inp = planner_input(
        {"Vesna": personal, "Theater": theater, "Normal": normal},
        {key: target(weapon=1) for key in ("Vesna", "Theater", "Normal")},
        tiers={"S": TierValue("S", "S", 1.0)},
        assignments={key: "S" for key in ("Vesna", "Theater", "Normal")},
    )
    inp.personal_priority_keys = {"Vesna"}
    inp.theater_priority_keys = {"Theater"}
    goals = run_plan(inp).global_plan
    characters = [goal.character_key for goal in goals]
    assert max(i for i, key in enumerate(characters) if key == "Vesna") < min(
        i for i, key in enumerate(characters) if key == "Theater")
    assert max(i for i, key in enumerate(characters) if key == "Theater") < min(
        i for i, key in enumerate(characters) if key == "Normal")
def test_simulation_does_not_mutate_resolved_input_state():
    char=CharacterState("A",1,0,{"auto":1,"skill":1,"burst":1},None)
    inp=planner_input({"A":char},{"A":target(weapon=1)})
    run_plan(inp)
    assert (char.level,char.ascension)==(1,0)


def test_plan_emits_concrete_steps_and_keeps_the_strategic_target():
    char=CharacterState("Aloy",20,1,{"auto":1,"skill":6,"burst":1},None)
    talents={"normal":{"enabled":False,"target":1,"importance":0.0},
             "skill":{"enabled":True,"target":10,"importance":1.0},
             "burst":{"enabled":False,"target":1,"importance":0.0}}
    result=run_plan(planner_input(
        {"Aloy":char},{"Aloy":target(level=90,ascension=6,weapon=1,talents=talents)},
        tiers={"S":TierValue("S","S",1.0,0)}, assignments={"Aloy":"S"}))
    keys=[goal.goal_key for goal in result.global_plan]
    assert len(keys) == len(set(keys))
    level=next(goal for goal in result.global_plan if goal.goal_key=="Aloy:CHARACTER_LEVEL")
    assert (level.current_value,level.target_value,level.next_milestone)==(20,90,40)
    asc=next(goal for goal in result.global_plan if goal.goal_key=="Aloy:CHARACTER_ASCENSION")
    assert (asc.current_value,asc.target_value,asc.next_milestone)==(1,6,2)
    skill=next(goal for goal in result.global_plan if goal.goal_key=="Aloy:TALENT_SKILL")
    assert (skill.current_value,skill.target_value,skill.next_milestone)==(6,10,7)
    assert [(step.current,step.target) for step in skill.milestone_chain[:2]] == [(6,7),(7,8)]


def test_level_next_milestone_stays_at_next_boundary_when_current_cap_requires_ascension():
    char=CharacterState("Amber",40,1,{"auto":1,"skill":1,"burst":1},None)
    goals,_=detect_goals(planner_input({"Amber":char},{"Amber":target(weapon=1)}))
    level=next(goal for goal in goals if goal.type==GoalType.CHARACTER_LEVEL)
    assert level.status==GoalStatus.BLOCKED
    assert (level.current_value,level.target_value,level.next_milestone)==(40,90,50)


def test_good_talent_fields_are_used_as_invested_base_ranks_not_constellation_bonus():
    """Fixture mirrors actual GOOD schema: C6 and its talent object retain base ranks."""
    c6_good_character = {"key":"Fischl","constellation":6,"talent":{"auto":1,"skill":8,"burst":4}}
    char = CharacterState(c6_good_character["key"],80,5,c6_good_character["talent"],None)
    assert char.talents == {"auto":1,"skill":8,"burst":4}
    skill_target = target(level=80,ascension=5,weapon=1,talents={
        "normal":{"enabled":False,"target":1,"importance":0.0},
        "skill":{"enabled":True,"target":10,"importance":1.0},
        "burst":{"enabled":False,"target":1,"importance":0.0}})
    goals, _ = detect_goals(planner_input({"Fischl":char},{"Fischl":skill_target}))
    skill_goal = next(goal for goal in goals if goal.type == GoalType.TALENT_SKILL)
    assert skill_goal.current_value == 8 and skill_goal.target_value == 10 and skill_goal.next_milestone == 9
    assert skill_goal.status == GoalStatus.BLOCKED
