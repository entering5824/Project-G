from .models import GoalStatus, UpgradeGoal


def resolve_dependencies(goals: list[UpgradeGoal]) -> list[UpgradeGoal]:
    """Resolve the explicit progression prerequisite references for a state snapshot."""
    by_key = {goal.goal_key: goal for goal in goals}
    for goal in goals:
        if goal.status == GoalStatus.COMPLETE:
            continue
        missing = [dep for dep in goal.dependencies if dep in by_key and by_key[dep].status != GoalStatus.ACTIONABLE]
        # A dependency not in the active goals is normally already satisfied;
        # blocked_by is set by the gap detector only when the state says otherwise.
        if goal.blocked_by or missing:
            goal.status = GoalStatus.BLOCKED
            goal.blocked_by = sorted(set(goal.blocked_by + missing))
        else:
            goal.status = GoalStatus.ACTIONABLE
    return goals


def actionable_frontier(goals: list[UpgradeGoal]) -> list[UpgradeGoal]:
    return sorted((goal for goal in goals if goal.status == GoalStatus.ACTIONABLE),
        key=lambda goal: (-goal.final_score, goal.character_key, goal.type.value, goal.goal_key))
