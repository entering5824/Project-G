"""SQLite orchestration adapter for Today planning.

Compilation and selection rules live inward. SQLite query/state/run mechanics are
split into ``sqlite.today`` persistence primitives so this facade only coordinates
the planner execution with those boundaries.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from projectg.application.planning.today import GenerateTodayPlan, TodayAccountContext
from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.domain.planning.today.config import TODAY_HORIZON
from projectg.domain.planning.today.selection import select_today_task, strategic_goal_order
from projectg.infrastructure.clock.game_clock import GameClock
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.mutation_uow import finalize_existing_transaction
from projectg.infrastructure.persistence.sqlite.planner_provenance import PlannerProvenance
from projectg.infrastructure.persistence.sqlite.today import (
    TodayAccountFacts,
    TodayContextReader,
    TodayPlanRunRepository,
    TodayStateRepository,
)


class TodayPlanner:
    def __init__(
        self,
        *,
        planner_factory,
        game_data: GameData,
        configuration: Settings,
        clock: Clock,
        game_clock: GameClock,
        id_generator: IdGenerator,
        availability: AvailabilityService | None = None,
        horizon: int = TODAY_HORIZON,
    ):
        self._planner_factory = planner_factory
        self.game = game_data
        self.configuration = configuration
        self.clock = clock
        self.game_clock = game_clock
        self.availability = availability
        self.horizon = horizon
        self._generate_today = GenerateTodayPlan(clock, horizon=horizon)
        self._context = TodayContextReader(configuration)
        self._state = TodayStateRepository()
        self._runs = TodayPlanRunRepository(id_generator, game_data)

    def generate(
        self,
        db: Session,
        limit: int | None = None,
        *,
        instant: datetime | None = None,
    ) -> dict:
        execution = self._planner_factory(db).execute(limit=limit)
        result = execution.result
        planner_input = execution.planner_input
        planner_config = execution.config
        account = self._context.account(db)

        region = account.server_region if account else self.configuration.server_region
        game_time = self.game_clock.now(region, instant)
        availability = self.availability or self._availability_for(account)
        context = TodayAccountContext(
            server_region=region,
            game_date=game_time.game_date,
            weekday=game_time.weekday,
            game_language=account.game_language if account else "en",
            world_level=account.world_level if account else None,
            resin=account.resin if account else None,
            weekly_claimed=account.weekly_claimed if account else (),
            unavailable_sources=account.unavailable_sources if account else (),
        )
        provenance = PlannerProvenance(db, self.configuration, self.game)
        output = self._generate_today.execute(
            result=result,
            game=self.game,
            account=context,
            availability=availability,
            context_hash=provenance.context_hash(),
            limit=limit,
        )
        if account:
            with finalize_existing_transaction(db):
                self._select_and_persist(
                    db,
                    account,
                    output,
                    result,
                    planner_input=planner_input,
                    planner_config=planner_config,
                    config=result.config_version,
                    dataset_hashes=provenance.dataset_hashes(),
                )
        return output

    def _availability_for(self, account: TodayAccountFacts | None) -> AvailabilityService:
        weekly_claimed = set(account.weekly_claimed) if account else set()
        recognized_claims = {
            key
            for key in weekly_claimed
            if key in self.game.bosses and self.game.bosses[key].weekly_limited
        }
        claimed_weekly_bosses = {self.game.bosses[key].name or key for key in recognized_claims}
        weekly_claim_count = len(claimed_weekly_bosses) + len(weekly_claimed - recognized_claims)
        return AvailabilityService(
            resin=account.resin if account else None,
            weekly_claimed=weekly_claimed,
            weekly_claim_count=weekly_claim_count,
            unavailable_sources=set(account.unavailable_sources) if account else set(),
        )

    @staticmethod
    def _account_ids(account) -> tuple[str, str | None]:
        account_id = getattr(account, "account_id", None) or getattr(account, "id")
        return account_id, getattr(account, "current_snapshot_id", None)

    def _select_and_persist(
        self,
        db: Session,
        account,
        output: dict,
        result,
        legacy_result=None,
        *,
        config: str,
        planner_input=None,
        planner_config=None,
        dataset_hashes: dict | None = None,
    ) -> None:
        # Compatibility for old direct tests/callers that passed an obsolete
        # planner-input positional argument before result.
        if legacy_result is not None:
            result = legacy_result
        if planner_config is None or planner_input is None:
            execution = self._planner_factory(db).execute(candidate_config=planner_config)
            planner_config = execution.config
            planner_input = execution.planner_input

        account_id, snapshot_id = self._account_ids(account)
        state = self._state.load(db, account_id)
        strategic_order = strategic_goal_order(getattr(result, "global_plan", ()) or ())
        selection = select_today_task(
            quick_actions=output["quickActions"],
            farming=output["farming"],
            unavailable=output["unavailable"],
            blocked=output["blocked"],
            state=state,
            strategic_order=strategic_order,
            unresolved=getattr(result, "unresolved", ()) or (),
            config_version=str(config),
            reorder_threshold=planner_config.reorder_threshold,
        )
        next_state = self._state.save(db, account_id, selection.next_state)

        output["primaryTask"] = selection.primary_task
        output["decisionMode"] = selection.decision_mode
        output["noActionReason"] = selection.no_action_reason
        output["alternativeTasks"] = list(selection.alternative_tasks)
        output["todayState"] = {
            "pursuedTaskId": next_state.pursued_task_id,
            "pursuedCharacterKey": next_state.pursued_character_key,
            "orderingGroup": next_state.ordering_group,
            "pinnedCharacterKey": next_state.pinned_character_key,
            "pinStatus": selection.pin_status,
            "switchThreshold": planner_config.reorder_threshold,
        }
        hashes = dataset_hashes or PlannerProvenance(db, self.configuration, self.game).dataset_hashes()
        self._runs.add(
            db,
            account_id=account_id,
            snapshot_id=snapshot_id,
            output=output,
            result=result,
            planner_input=planner_input,
            planner_config=planner_config,
            config_version=str(config),
            dataset_hashes=hashes,
        )
