from copy import deepcopy
from .dependencies import actionable_frontier, resolve_dependencies
from .gap_detector import detect_goals
from .models import GoalStatus, GoalType, MilestoneStep, PlannerInput, PlannerResult, UpgradeGoal, UnresolvedIssue
from .scorer import score_goal


def _score_and_resolve(goals: list[UpgradeGoal], inp: PlannerInput) -> list[UpgradeGoal]:
    for goal in goals:
        score_goal(goal, inp)
    return resolve_dependencies(goals)


def _is_ranked(goal: UpgradeGoal, inp: PlannerInput) -> bool:
    # Missing-tier characters remain visible through Data Health and the
    # dedicated unranked list. Only an explicit priority override can place an
    # otherwise-unranked character into the strategic queue. This rule is
    # identical for production and direct engine callers: low level or an
    # enabled talent never silently acts as an implicit tier.
    if goal.character_key in inp.personal_priority_keys or goal.character_key in inp.theater_priority_keys:
        return True
    if inp.planner_controls.get(goal.character_key) == "IGNORE":
        return False
    if goal.priority_mode == "PRIORITIZED":
        return True
    if inp.tier_scores:
        score = inp.tier_scores.get(goal.character_key)
        return score is not None and (score >= inp.minimum_tier_score or
                                      inp.planner_controls.get(goal.character_key) == "FORCE_INCLUDE")
    if inp.planner_controls:
        return False
    return bool(goal.tier_configured or goal.priority_mode == "PRIORITIZED"
                or inp.include_unranked_in_plan)


def _simulate(goal: UpgradeGoal, inp: PlannerInput) -> None:
    char = inp.characters[goal.character_key]
    if goal.type == GoalType.CHARACTER_LEVEL:
        char.level = int(goal.action_target)
    elif goal.type == GoalType.CHARACTER_ASCENSION:
        char.ascension = int(goal.action_target)
    elif goal.type == GoalType.TALENT_AUTO:
        char.talents["auto"] = int(goal.action_target)
    elif goal.type == GoalType.TALENT_SKILL:
        char.talents["skill"] = int(goal.action_target)
    elif goal.type == GoalType.TALENT_BURST:
        char.talents["burst"] = int(goal.action_target)
    elif goal.type == GoalType.WEAPON_LEVEL and char.weapon is not None:
        char.weapon.level = int(goal.action_target)


def _override_order(mode: str) -> int:
    return {"PRIORITIZED":0,"NORMAL":1,"DEPRIORITIZED":2}.get(mode,1)


def _priority_group(goal: UpgradeGoal, inp: PlannerInput) -> int:
    if goal.character_key in inp.personal_priority_keys:
        return 0
    if goal.character_key in inp.theater_priority_keys:
        return 1
    return 2


def _has_unknown_equipped_rv(goal: UpgradeGoal, inp: PlannerInput) -> bool:
    character = inp.characters[goal.character_key]
    return any(item.get("rv") is None for item in character.artifacts.values())


def _select_next(frontier: list[UpgradeGoal], current_goals: list[UpgradeGoal],
                 inp: PlannerInput) -> UpgradeGoal:
    """Choose the best actionable upgrade across the whole account."""
    return min(frontier, key=lambda goal: (_priority_group(goal, inp), -goal.final_score, -goal.importance,
        goal.character_key, goal.type.value, goal.goal_key))


def run_simulation(inp: PlannerInput, generated_at: str, planner_version: str,
                   config_version: str) -> PlannerResult:
    # The plan's simulated progression must never mutate the resolved account
    # state supplied by the repository/service.
    working = deepcopy(inp)
    initial_goals, unresolved = detect_goals(working)
    initial_goals = _score_and_resolve(initial_goals, working)
    for goal in initial_goals:
        goal.planning_group = ("PERSONAL" if goal.character_key in working.personal_priority_keys
                               else "THEATER" if goal.character_key in working.theater_priority_keys
                               else "NORMAL")
        if goal.planning_group == "PERSONAL":
            goal.reason_codes.append("PERSONAL_BUILD_PRIORITY")
        elif goal.planning_group == "THEATER":
            goal.reason_codes.append("THEATER_PREPARATION_PRIORITY")
    blocked_rv_characters = {
        key for key in working.personal_priority_keys
        if key in working.characters and any(item.get("rv") is None
                                             for item in working.characters[key].artifacts.values())
    }
    for key in sorted(blocked_rv_characters):
        slots = sorted(slot for slot, item in working.characters[key].artifacts.items()
                       if item.get("rv") is None)
        unresolved.append(UnresolvedIssue("PERSONAL_PRIORITY_RV_REQUIRED", key, "warning",
            "Điền RV cho thánh di vật đang trang bị để tiếp tục đề xuất build nhân vật được ưu tiên.",
            {"slots": slots}))
    for goal in initial_goals:
        if goal.character_key in blocked_rv_characters:
            goal.status = GoalStatus.BLOCKED
            goal.reason_codes.append("PERSONAL_PRIORITY_RV_REQUIRED")
    generated_count = len(initial_goals)
    eligible_goals = [goal for goal in initial_goals if _is_ranked(goal, working)]
    blocked_count = sum(goal.status == GoalStatus.BLOCKED for goal in eligible_goals)
    actionable_count = sum(goal.status == GoalStatus.ACTIONABLE for goal in eligible_goals)

    # Resolve complete execution chains internally. These steps are never
    # separate public goals; public rows retain the original state and score.
    actions: list[UpgradeGoal] = []
    emitted_non_progression: set[str] = set()
    max_internal_steps = max(working.config.horizon, len(working.characters) * (
        len(working.config.level_milestones) + len(working.config.weapon_milestones) + 60))
    internal_steps = 0
    while internal_steps < max_internal_steps:
        internal_steps += 1
        current_goals, _ = detect_goals(working)
        current_goals = _score_and_resolve(current_goals, working)
        for goal in current_goals:
            if goal.character_key in blocked_rv_characters:
                goal.status = GoalStatus.BLOCKED
            if goal.character_key in working.personal_priority_keys:
                goal.planning_group = "PERSONAL"
            elif goal.character_key in working.theater_priority_keys:
                goal.planning_group = "THEATER"
        frontier = actionable_frontier([goal for goal in current_goals if _is_ranked(goal, working)
                                        and goal.character_key not in blocked_rv_characters])
        frontier = [goal for goal in frontier if goal.type != GoalType.ARTIFACT_QUALITY
                    or goal.goal_key not in emitted_non_progression]
        if not frontier:
            break
        selected = deepcopy(_select_next(frontier, current_goals, working))
        actions.append(selected)
        if selected.type == GoalType.ARTIFACT_QUALITY:
            emitted_non_progression.add(selected.goal_key)
        _simulate(selected, working)

    # Keep otherwise-unreachable account goals visible at the bottom of the
    # roadmap with their blocked status and explanation. They are not simulated
    # as completed steps and never displace actionable goals from the front.
    emitted_goal_keys = {goal.goal_key for goal in actions}
    remaining = [goal for goal in eligible_goals
                 if goal.status != GoalStatus.COMPLETE and goal.goal_key not in emitted_goal_keys]
    remaining.sort(key=lambda goal:(_priority_group(goal, working), -goal.final_score,
                                    goal.character_key,goal.type.value,goal.goal_key))
    actions.extend(deepcopy(remaining))

    # Simulation describes execution steps, never independent strategic rows.
    # Project original account facts and scores once per semantic component.
    originals = {goal.goal_key: goal for goal in eligible_goals}
    semantic_goals: dict[str, UpgradeGoal] = {}
    for action in actions:
        if action.goal_key not in semantic_goals:
            semantic_goals[action.goal_key] = deepcopy(originals[action.goal_key])
        if action.type != GoalType.ARTIFACT_QUALITY and action.status == GoalStatus.ACTIONABLE:
            semantic_goals[action.goal_key].milestone_chain.append(
                MilestoneStep(action.current_value, action.action_target))
    global_goals = list(semantic_goals.values())[:working.config.horizon]

    return PlannerResult(
        generated_at=generated_at,
        planner_version=planner_version,
        config_version=config_version,
        configured_characters=len(working.character_targets.keys() & working.characters.keys()),
        configured_tiers=sum(1 for key in working.characters if working.tier_assignments.get(key) in working.tiers),
        total_characters=len(working.characters),
        generated_goals=generated_count,
        blocked_goals=blocked_count,
        actionable_goals=actionable_count,
        global_plan=global_goals,
        unresolved=unresolved,
        tier_fallback=working.config.tier_fallback,
    )
