from dataclasses import replace

from projectg.application.ports.outbound.clock import Clock
from projectg.domain.planning.config import PlannerConfig
from projectg.domain.planning.engine import PlannerEngine
from projectg.domain.planning.models import GoalType, PlannerInput, PlannerResult, UnresolvedIssue


class GeneratePlan:
    """Run the planner from normalized input without knowing where that input came from."""

    def __init__(self, clock: Clock):
        self._clock = clock

    def execute(
        self,
        planner_input: PlannerInput,
        base_config: PlannerConfig,
        *,
        repository_issues: list[dict] | tuple[dict, ...] = (),
        limit: int | None = None,
    ) -> PlannerResult:
        config = replace(
            base_config,
            horizon=limit if limit is not None else base_config.horizon,
        )
        # Repository adapters may have built the input with the same config object.
        # Keep the application boundary authoritative when callers override horizon.
        planner_input = replace(planner_input, config=config)
        generated_at = self._clock.now().isoformat().replace("+00:00", "Z")
        result = PlannerEngine(config).run(planner_input, generated_at=generated_at)

        result.artifact_enabled_characters = sum(
            1
            for key in planner_input.characters
            if (planner_input.character_targets.get(key) or {}).get("artifact", {}).get("enabled")
        )
        result.artifact_evaluated_characters = sum(
            1
            for key in planner_input.artifact_evaluations
            if (planner_input.character_targets.get(key) or {}).get("artifact", {}).get("enabled")
        )

        artifact_goals = [
            goal
            for goal in result.global_plan[: config.horizon]
            if goal.type == GoalType.ARTIFACT_QUALITY
        ]
        domain_value: dict[str, float] = {}
        for goal in artifact_goals:
            for domain in goal.artifact_domain_candidates:
                domain_value[domain["key"]] = (
                    domain_value.get(domain["key"], 0.0) + goal.final_score
                )

        for goal in artifact_goals:
            if goal.artifact_domain_candidates:
                goal.artifact_domain = sorted(
                    goal.artifact_domain_candidates,
                    key=lambda domain: (-domain_value.get(domain["key"], 0), domain["key"]),
                )[0]
            else:
                result.unresolved.append(
                    UnresolvedIssue(
                        "ARTIFACT_DOMAIN_MISSING",
                        goal.character_key,
                        "warning",
                        "Artifact targets need at least one set mapped to a local artifact domain.",
                        {"goalKey": goal.goal_key},
                    )
                )

        result.unresolved.extend(
            UnresolvedIssue(
                issue["code"],
                issue.get("characterKey"),
                issue["severity"],
                issue["message"],
                issue.get("details") or {},
            )
            for issue in repository_issues
        )
        return result
