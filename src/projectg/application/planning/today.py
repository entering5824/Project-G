"""Application orchestration for compiling the persisted Global Plan into Today output.

This module deliberately knows nothing about SQLAlchemy or SQLite.  Persistence
adapters supply the normalized planner result/input and account runtime facts.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from projectg.application.ports.outbound.clock import Clock
from projectg.domain.costs.models import CostStatus, ResolvedCost
from projectg.domain.costs.resolver import resolve_cost, resolve_requirements
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.models import PlannerResult
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.domain.planning.today.compiler import TaskCompiler
from projectg.domain.planning.today.config import TODAY_HORIZON


@dataclass(frozen=True)
class TodayAccountContext:
    server_region: str
    game_date: date
    weekday: str
    game_language: str = "en"
    world_level: int | None = None
    resin: int | None = None
    weekly_claimed: tuple[str, ...] = ()
    unavailable_sources: tuple[str, ...] = ()


class GenerateTodayPlan:
    """Compile a PlannerResult into Today's actionable read model."""

    def __init__(self, clock: Clock, *, horizon: int = TODAY_HORIZON):
        self._clock = clock
        self._horizon = horizon

    @staticmethod
    def _issue_dict(issue: Any) -> dict[str, Any]:
        if isinstance(issue, dict):
            return dict(issue)
        to_dict = getattr(issue, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        return {
            "code": getattr(issue, "code", "UNKNOWN"),
            "characterKey": getattr(issue, "character_key", None),
            "severity": getattr(issue, "severity", "warning"),
            "message": getattr(issue, "message", ""),
            "details": getattr(issue, "details", {}) or {},
        }

    @staticmethod
    def _weapon_ascension_available(game: GameData, goal: Any) -> bool:
        return bool(
            goal.weapon_key
            and f"weapon_ascension:{goal.weapon_key}" in game.steps
        )

    def execute(
        self,
        *,
        result: PlannerResult,
        game: GameData,
        account: TodayAccountContext,
        availability: AvailabilityService,
        context_hash: str | None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        horizon = limit or self._horizon
        goals = []
        seen_candidate_lanes: set[str] = set()
        for goal in result.global_plan:
            if len(goals) >= horizon:
                break
            if goal.goal_key in seen_candidate_lanes:
                continue
            seen_candidate_lanes.add(goal.goal_key)
            goals.append(goal)

        unresolved = [self._issue_dict(item) for item in result.unresolved]
        if game.error:
            unresolved.append({"code": "GAME_DATA_MISSING", "severity": "warning",
                               "characterKey": None, "message": "Cost estimates are unavailable; strategic goals are retained.",
                               "details": game.error})

        ranked: list[tuple[Any, ResolvedCost]] = []
        for goal in goals:
            if goal.type.value == "ARTIFACT_QUALITY":
                ranked.append((goal, ResolvedCost({}, CostStatus.ESTIMATED, flags=["RNG_HEAVY"])))
                continue
            if goal.status.value == "BLOCKED":
                cost = ResolvedCost({}, CostStatus.ESTIMATED, flags=["PREREQUISITE_BLOCKED"])
            else:
                value = int(goal.next_milestone if goal.next_milestone is not None else goal.target_value)
                requirements = resolve_requirements(game, goal, value)
                if (
                    goal.type.value == "WEAPON_LEVEL"
                    and value > 20
                    and not self._weapon_ascension_available(game, goal)
                ):
                    requirements = None
                cost = resolve_cost(game, requirements)
            if (
                goal.type.value == "WEAPON_LEVEL"
                and int(goal.next_milestone if goal.next_milestone is not None else goal.target_value) > 20
                and not self._weapon_ascension_available(game, goal)
            ):
                cost.status = CostStatus.COST_DATA_MISSING
                cost.flags.append("WEAPON_ASCENSION_COST_DATA_MISSING")
            ranked.append((goal, cost))

        compiler = TaskCompiler(game, availability)
        sections, compile_issues = compiler.compile(
            ranked,
            game_date=account.game_date,
            server_region=account.server_region,
            unresolved=unresolved,
        )
        counts = {key: len(value) for key, value in sections.items()}
        missing_targets = sum(
            int((issue.details or {}).get("count", 1))
            for issue in result.unresolved
            if issue.code == "TARGET_NOT_CONFIGURED"
        )
        missing_profiles = sum(
            1 for issue in result.unresolved if issue.code == "BUILD_PROFILE_MISSING"
        )
        knowledge_ready = not any(
            issue.code in {"BUILD_KNOWLEDGE_COVERAGE", "BUILD_PACK_INVALID"}
            for issue in result.unresolved
        )

        output: dict[str, Any] = {
            "generatedAt": self._clock.now().isoformat(),
            "gameDate": account.game_date.isoformat(),
            "weekday": account.weekday,
            "serverRegion": account.server_region,
            "planningWindow": len(goals),
            "accountSettings": {
                "gameLanguage": account.game_language,
                "worldLevel": account.world_level,
                "resin": account.resin,
                "weeklyClaimed": list(account.weekly_claimed),
                "unavailableSources": list(account.unavailable_sources),
            },
            "plannerVersion": result.planner_version,
            "plannerConfigVersion": result.config_version,
            "contextHash": context_hash,
            "globalGoals": [
                {"rank": rank, "goalKey": goal.goal_key, "score": round(goal.final_score, 2)}
                for rank, goal in enumerate(goals, 1)
            ],
            "coverage": {
                "ownedCharacters": result.total_characters,
                "configuredTargets": result.configured_characters,
                "missingTargets": missing_targets,
                "missingProfiles": missing_profiles,
                "buildKnowledgeReady": knowledge_ready,
            },
            "counts": counts,
            "quickActions": sections["quickActions"],
            "farming": sections["farming"],
            "unavailable": sections["unavailable"],
            "blocked": sections["blocked"],
            "unresolved": compile_issues,
        }

        return output

