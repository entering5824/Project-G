"""Evaluate planner/data quality from typed facts and inward-facing services."""

from collections.abc import Callable

from projectg.application.health.report import build_data_health_report
from projectg.application.ports.outbound.data_health_gateway import DataHealthFactsGateway
from projectg.application.ports.outbound.game_data_gateway import GameDataGateway
from projectg.application.ports.outbound.support_gateway import SupportData
from projectg.application.use_cases.planning.run_planner import PlannerExecution
from projectg.domain.costs.engine import CostEngine


class GetDataHealth:
    def __init__(
        self,
        facts: DataHealthFactsGateway,
        planner_execute: Callable[[], PlannerExecution],
        game_data: GameDataGateway,
    ):
        self._facts = facts
        self._planner_execute = planner_execute
        self._game_data = game_data

    def execute(self) -> SupportData:
        facts = self._facts.load_facts()
        game = self._game_data.load()

        planner_result = None
        plan_cost = None
        backend_errors: list[str] = []
        try:
            planner_result = self._planner_execute().result
            plan_cost = CostEngine(game).required_materials(planner_result.global_plan)
        except Exception as exc:
            backend_errors.append(str(exc))

        missing_characters = tuple(
            key for key in facts.character_keys if key not in game.characters
        )
        missing_weapons = tuple(
            key for key in facts.equipped_weapon_keys if key not in game.weapons
        )
        return SupportData(build_data_health_report(
            planner_result=planner_result,
            artifact_quality_configured=facts.artifact_quality_configured,
            game_error=game.error,
            plan_cost=plan_cost,
            missing_character_keys=missing_characters,
            missing_weapon_keys=missing_weapons,
            backend_errors=backend_errors,
            account_available=facts.account_available,
        ))
