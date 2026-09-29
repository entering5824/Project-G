from projectg.domain.planning.engine import action_to_dict
from projectg.domain.planning.models import PlannerResult


def plan_result_to_dict(result: PlannerResult) -> dict:
    """Project a planner result into the stable application response contract."""
    unresolved = [item.to_dict() for item in result.unresolved]
    counts: dict[str, int] = {}
    for item in unresolved:
        counts[item["code"]] = counts.get(item["code"], 0) + int(
            (item.get("details") or {}).get("count", 1)
        )
    return {
        "generatedAt": result.generated_at,
        "plannerVersion": result.planner_version,
        "plannerConfigVersion": result.config_version,
        "tierFallback": result.tier_fallback,
        "coverage": {
            "configuredCharacters": result.configured_characters,
            "totalCharacters": result.total_characters,
            "missingTargets": counts.get("TARGET_NOT_CONFIGURED", 0),
            "missingProfiles": counts.get("BUILD_PROFILE_MISSING", 0),
            "buildKnowledgeCoverage": next(
                (
                    item.get("details")
                    for item in unresolved
                    if item.get("code")
                    in {"BUILD_KNOWLEDGE_COVERAGE", "BUILD_KNOWLEDGE_DEPTH"}
                ),
                None,
            ),
            "missingTiers": counts.get("TIER_NOT_CONFIGURED", 0),
            "ownedCharacters": result.total_characters,
            "configuredTargets": result.configured_characters,
            "configuredTiers": result.configured_tiers,
            "artifactEnabledCharacters": result.artifact_enabled_characters,
            "artifactEvaluatedCharacters": result.artifact_evaluated_characters,
            "artifactMissingEvaluations": max(
                0,
                result.artifact_enabled_characters - result.artifact_evaluated_characters,
            ),
        },
        "counts": {
            "generatedGoals": result.generated_goals,
            "blockedGoals": result.blocked_goals,
            "actionableGoals": result.actionable_goals,
            "plannedActions": len(result.global_plan),
        },
        "global": [
            action_to_dict(goal, rank)
            for rank, goal in enumerate(result.global_plan, start=1)
        ],
        "unresolved": unresolved,
    }


def find_action_detail(result: PlannerResult, action_id: str) -> dict | None:
    for rank, goal in enumerate(result.global_plan, start=1):
        if goal.id == action_id:
            return {
                "action": action_to_dict(goal, rank),
                "scoreBreakdown": (
                    goal.score_breakdown.to_dict() if goal.score_breakdown else None
                ),
                "reasonCodes": goal.reason_codes,
                "dependencies": goal.dependencies,
                "blockedBy": goal.blocked_by,
                "plannerVersion": result.planner_version,
                "plannerConfigVersion": result.config_version,
            }
    return None
