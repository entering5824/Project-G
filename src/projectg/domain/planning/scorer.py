from .models import PlannerInput, UpgradeGoal
from .progress import clamp
from .reasons import reason_codes
from .tiers import investment_multiplier


def score_goal(goal: UpgradeGoal, inp: PlannerInput) -> UpgradeGoal:
    config = inp.config
    weights = config.weights
    base_priority = (
        weights["deficiency"] * goal.deficiency
        + weights["importance"] * goal.importance
        + weights["tier"] * goal.tier_value
        + weights["team"] * goal.team_value
        + weights["completion"] * goal.completion_value
    )
    goal.base_score = base_priority * 100.0
    efficiency = goal.efficiency if goal.efficiency is not None else config.efficiency
    efficiency_modifier = config.efficiency_modifier_base + config.efficiency_modifier_weight * efficiency
    tier_multiplier = investment_multiplier(inp.tier_scores.get(goal.character_key))
    goal.final_score = clamp(goal.base_score * efficiency_modifier * config.confidence * goal.priority_override * tier_multiplier, 0.0, 100.0)
    from .models import ScoreBreakdown
    goal.score_breakdown = ScoreBreakdown(
        deficiency=goal.deficiency, importance=goal.importance, tier=goal.tier_value,
        team=goal.team_value, completion=goal.completion_value, base_score=goal.base_score,
        efficiency=efficiency, efficiency_modifier=efficiency_modifier,
        confidence=config.confidence, priority_override=goal.priority_override,
        final_score=goal.final_score, tier_configured=goal.tier_configured,
        tier_priority_multiplier=tier_multiplier,
        tier_label=goal.tier_label,
        priority_mode=goal.priority_mode,
        saved_team_member=goal.saved_team_member,
        primary_team_member=goal.primary_team_member,
        completion_explanation={
            0.0: "Normal improvement",
            0.35: "Completes one deterministic target component",
            0.60: "Character is near deterministic core completion",
            1.0: "Completes all enabled deterministic core components",
        }.get(goal.completion_value, "Deterministic completion bonus"),
    )
    goal.reason_codes = reason_codes(goal)
    return goal
