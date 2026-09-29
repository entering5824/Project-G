from .models import GoalType, UpgradeGoal


REASON_INPUTS = {
    "HIGH_DEFICIENCY": ("deficiency", "deficiency"),
    "HIGH_IMPACT_COMPONENT": ("componentImportance", "importance"),
    "HIGH_TIER_CHARACTER": ("tier", "tier"),
    "SAVED_TEAM_MEMBER": ("team", "team"),
    "PRIMARY_TEAM_MEMBER": ("team", "team"),
    "MANUAL_PRIORITY_OVERRIDE": ("priorityOverride", "priority"),
    "UNRANKED_CHARACTER": ("tier", "tier"),
    "NEAR_CHARACTER_COMPLETION": ("completion", "completion"),
    "COMPLETES_CHARACTER_CORE": ("completion", "completion"),
    "WEAPON_FAR_BELOW_TARGET": ("componentGap", "deficiency"),
    "TALENT_BELOW_TARGET": ("componentGap", "deficiency"),
    "CHARACTER_LEVEL_BELOW_TARGET": ("componentGap", "deficiency"),
    "ASCENSION_BELOW_TARGET": ("componentGap", "deficiency"),
    "ARTIFACT_TARGET_REACHED": ("artifact", "artifactStatus"),
    "PERSONAL_BUILD_PRIORITY": ("planningPriority", "planningGroup"),
    "THEATER_PREPARATION_PRIORITY": ("planningPriority", "planningGroup"),
    "PERSONAL_PRIORITY_RV_REQUIRED": ("missingInput", "rule"),
}


def structured_reasons(goal: UpgradeGoal) -> list[dict]:
    """Pair each explanation code with the persisted input that produced it."""
    result = []
    for code in goal.reason_codes:
        reason_type, source = REASON_INPUTS.get(code, ("plannerRule", "rule"))
        if source == "deficiency":
            value = round(goal.deficiency, 4)
        elif source == "importance":
            value = ("primary" if goal.importance >= 0.8 else
                     "secondary" if goal.importance > 0 else "ignore")
        elif source == "tier":
            value = goal.tier_label if goal.tier_configured else "UNRANKED"
        elif source == "team":
            value = {"savedTeamMember": goal.saved_team_member,
                     "primaryTeamMember": goal.primary_team_member}
        elif source == "priority":
            value = goal.priority_mode
        elif source == "completion":
            value = round(goal.completion_value, 4)
        elif source == "artifactStatus":
            value = goal.artifact_status
        else:
            value = code
        result.append({"code": code, "type": reason_type, "value": value})
    return result


def goal_explanation(goal: UpgradeGoal) -> dict:
    component = {
        GoalType.CHARACTER_LEVEL: "level",
        GoalType.CHARACTER_ASCENSION: "ascension",
        GoalType.TALENT_AUTO: "normal",
        GoalType.TALENT_SKILL: "skill",
        GoalType.TALENT_BURST: "burst",
        GoalType.WEAPON_LEVEL: "weapon",
        GoalType.ARTIFACT_QUALITY: "artifact",
    }[goal.type]
    return {
        "characterKey": goal.character_key,
        "component": component,
        "milestoneLabel": f"{goal.current_value} → {goal.next_milestone if goal.next_milestone is not None else goal.target_value}",
        "milestone": {"from": goal.current_value,
                      "to": goal.next_milestone if goal.next_milestone is not None else goal.target_value},
        "reasons": structured_reasons(goal),
    }


def reason_codes(goal: UpgradeGoal) -> list[str]:
    reasons: list[str] = list(goal.reason_codes if goal.type == GoalType.ARTIFACT_QUALITY else [])
    if goal.deficiency >= 0.65:
        reasons.append("HIGH_DEFICIENCY")
    if goal.importance >= 0.80:
        reasons.append("HIGH_IMPACT_COMPONENT")
    if goal.tier_value >= 0.80:
        reasons.append("HIGH_TIER_CHARACTER")
    if goal.primary_team_member:
        reasons.append("PRIMARY_TEAM_MEMBER")
    elif goal.saved_team_member:
        reasons.append("SAVED_TEAM_MEMBER")
    if goal.completion_value == 0.60:
        reasons.append("NEAR_CHARACTER_COMPLETION")
    elif goal.completion_value == 1.00:
        reasons.append("COMPLETES_CHARACTER_CORE")
    if goal.type == GoalType.WEAPON_LEVEL and goal.deficiency >= 0.50:
        reasons.append("WEAPON_FAR_BELOW_TARGET")
    elif goal.type in (GoalType.TALENT_AUTO, GoalType.TALENT_SKILL, GoalType.TALENT_BURST):
        reasons.append("TALENT_BELOW_TARGET")
    elif goal.type == GoalType.CHARACTER_LEVEL:
        reasons.append("CHARACTER_LEVEL_BELOW_TARGET")
    elif goal.type == GoalType.CHARACTER_ASCENSION:
        reasons.append("ASCENSION_BELOW_TARGET")
    elif goal.type == GoalType.ARTIFACT_QUALITY and goal.artifact_status == "COMPLETE":
        reasons.append("ARTIFACT_TARGET_REACHED")
    if goal.priority_mode != "NORMAL":
        reasons.append("MANUAL_PRIORITY_OVERRIDE")
    if goal.planning_group == "PERSONAL":
        reasons.append("PERSONAL_BUILD_PRIORITY")
    elif goal.planning_group == "THEATER":
        reasons.append("THEATER_PREPARATION_PRIORITY")
    if not goal.tier_configured:
        reasons.append("UNRANKED_CHARACTER")
    return list(dict.fromkeys(reasons))


def summary(goal: UpgradeGoal) -> str:
    return goal.summary
