from .models import GoalType
from .config import DEFAULT_PLANNER_CONFIG
from .models import PlannerInput, PlannerResult, UpgradeGoal
from .reasons import structured_reasons
from .simulator import run_simulation


class PlannerEngine:
    """Orchestrates pure goal generation, dependency resolution, scoring and simulation."""

    def __init__(self, config=DEFAULT_PLANNER_CONFIG):
        self.config = config

    def run(self, planner_input: PlannerInput, *, generated_at: str) -> PlannerResult:
        """Run planning with a timestamp supplied by the outer application layer."""
        planner_input.config = self.config
        return run_simulation(planner_input, generated_at, self.config.planner_version, self.config.config_version)


def action_to_dict(goal: UpgradeGoal, rank: int) -> dict:
    current = goal.current_value
    target = goal.target_value
    return {
        "rank": rank,
        "id": goal.id,
        "goalKey": goal.goal_key,
        "character": {"key": goal.character_key, "name": goal.character_key},
        "type": goal.type.value,
        "status": goal.status.value,
        "title": f"{goal.component_label} {current} → {goal.strategic_target if goal.strategic_target is not None else target}",
        "current": {"value": current},
        "target": {"value": target},
        "nextMilestone": {"value": goal.next_milestone} if goal.next_milestone is not None else None,
        "milestoneChain": [{"from": step.current, "to": step.target} for step in goal.milestone_chain],
        "strategicTarget": {"value": goal.strategic_target},
        "score": round(goal.final_score, 2),
        "normalizedScore": goal.current_value if goal.type == GoalType.ARTIFACT_QUALITY else None,
        "qualityLabel": goal.artifact_quality_label,
        "targetQuality": goal.artifact_target_quality,
        "targetScore": goal.artifact_target_score,
        "weakSlots": goal.artifact_weak_slots,
        "artifactStatus": goal.artifact_status,
        "artifactStale": goal.artifact_stale,
        "artifactDeveloperInput": goal.artifact_developer_input,
        "recommendedDomain": goal.artifact_domain,
        "candidateDomains": goal.artifact_domain_candidates,
        "recommendedArtifactSets": goal.artifact_recommended_sets,
        "candidateClass": goal.artifact_candidate_class,
        "summary": goal.summary,
        "reasonCodes": goal.reason_codes,
        "reasons": structured_reasons(goal),
        "availability": {"actionable": goal.status.value == "ACTIONABLE"},
        "dependencies": goal.dependencies,
        "blockedBy": goal.blocked_by,
        "tierConfigured": goal.tier_configured,
        "tierKey": goal.tier_key,
        "tierLabel": goal.tier_label,
        "tierFallbackUsed": not goal.tier_configured,
        "savedTeamMember": goal.saved_team_member,
        "primaryTeamMember": goal.primary_team_member,
        "deficiencyMethod": {
            "CHARACTER_LEVEL": "character_level_deficiency (milestone normalized)",
            "CHARACTER_ASCENSION": "ascension_deficiency (remaining phases)",
            "TALENT_AUTO": "talent_deficiency (normalized rank gap)",
            "TALENT_SKILL": "talent_deficiency (normalized rank gap)",
            "TALENT_BURST": "talent_deficiency (normalized rank gap)",
            "WEAPON_LEVEL": "weapon_level_deficiency (milestone normalized)",
            "ARTIFACT_QUALITY": "artifact_quality_configured_thresholds",
        }.get(goal.type.value),
        "priorityMode": goal.priority_mode,
        "planningGroup": goal.planning_group,
        "scoreBreakdown": goal.score_breakdown.to_dict() if goal.score_breakdown else None,
        "weapon": ({"instanceId": goal.weapon_instance_id, "key": goal.weapon_key,
                    "currentLevel": goal.current_value, "targetLevel": goal.strategic_target,
                    "nextMilestone": goal.next_milestone,
                    "currentAscension": goal.weapon_ascension}
                   if goal.weapon_instance_id else None),
    }
