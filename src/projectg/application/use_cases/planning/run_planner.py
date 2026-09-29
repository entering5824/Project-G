"""Execute the planner from inward-facing ports only."""

from dataclasses import dataclass

from projectg.application.planning.generate import GeneratePlan
from projectg.application.planning.input import prepare_planner_input
from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgeGateway
from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.game_data_gateway import GameDataGateway
from projectg.application.ports.outbound.planner_gateway import PlannerGateway
from projectg.domain.planning.config import PlannerConfig
from projectg.domain.planning.models import PlannerInput, PlannerResult


@dataclass(frozen=True)
class PlannerExecution:
    result: PlannerResult
    planner_input: PlannerInput
    config: PlannerConfig


class RunPlanner:
    def __init__(
        self,
        gateway: PlannerGateway,
        game_data: GameDataGateway,
        build_knowledge: BuildKnowledgeGateway,
        clock: Clock,
    ):
        self._gateway = gateway
        self._game_data = game_data
        self._build_knowledge = build_knowledge
        self._generate = GeneratePlan(clock)

    def execute(
        self,
        *,
        limit: int | None = None,
        candidate_config: PlannerConfig | None = None,
    ) -> PlannerExecution:
        config = candidate_config or self._gateway.load_config()
        facts = self._gateway.load_facts()
        game = self._game_data.load()
        build_pack = (
            self._build_knowledge.load(set(game.characters))
            if facts.has_snapshot
            else None
        )
        prepared = prepare_planner_input(facts, game, build_pack, config)
        result = self._generate.execute(
            prepared.value,
            config,
            repository_issues=prepared.issues,
            limit=limit,
        )
        return PlannerExecution(result=result, planner_input=prepared.value, config=config)
