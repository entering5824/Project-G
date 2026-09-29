"""SQLite adapter for immutable planner runs and Today pin persistence."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.planner_state_gateway import (
    PinContext,
    PinState,
    PlanRunReplay,
    PlanRunSummary,
)
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import PlanRun, SnapshotCharacter, TodayState
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqlitePlannerStateGateway:
    def __init__(self, session_factory: Callable[[], Session],
                 maintenance_gate: DatabaseMaintenanceGate, configuration: Settings,
                 today_planner_factory, mutation_uow: SqliteMutationUnitOfWork):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration
        self._today_planner_factory = today_planner_factory
        self._mutations = mutation_uow

    def _account(self, db: Session):
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    def list_runs(self, limit: int) -> tuple[PlanRunSummary, ...]:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                rows = db.scalars(
                    select(PlanRun)
                    .where(PlanRun.account_id == self._configuration.account_id)
                    .order_by(PlanRun.created_at.desc(), PlanRun.id.desc())
                    .limit(limit)
                ).all()
                return tuple(PlanRunSummary(
                    id=row.id,
                    created_at=row.created_at.isoformat(),
                    kind=row.kind,
                    snapshot_id=row.snapshot_id,
                    planner_config_version=row.planner_config_version,
                    primary_task=row.result_json.get("primaryTask"),
                ) for row in rows)

    def replay_run(self, run_id: str) -> PlanRunReplay:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                row = db.get(PlanRun, run_id)
                if row is None or row.account_id != self._configuration.account_id:
                    raise ValueError("PlanRun was not found.")
                return PlanRunReplay(
                    plan_run_id=row.id,
                    recorded_at=row.created_at.isoformat(),
                    result=row.result_json,
                    normalized_input=row.normalized_input_json,
                    target_versions=row.target_versions_json,
                    planner_config_version=row.planner_config_version,
                    source_availability=row.source_availability_json,
                    context=row.context_json,
                    hysteresis_state=row.hysteresis_state_json,
                    engine_version=row.engine_version,
                    game_data_version=row.game_data_version,
                    rv_formula_version=row.rv_formula_version,
                    switch_threshold=row.switch_threshold,
                )

    def load_pin_context(self, character_key: str) -> PinContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = self._account(db)
                owned = bool(
                    account.current_snapshot_id
                    and db.get(SnapshotCharacter, (account.current_snapshot_id, character_key)) is not None
                )
                if not owned:
                    return PinContext(owned=False, today_plan={})
                plan = self._today_planner_factory().generate(db)
                return PinContext(owned=True, today_plan=plan)

    def owns_character(self, character_key: str) -> bool:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = self._account(db)
                return bool(
                    account.current_snapshot_id
                    and db.get(SnapshotCharacter, (account.current_snapshot_id, character_key)) is not None
                )

    def persist_pin(self, character_key: str | None) -> PinState:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._account(db)
            state = db.get(TodayState, account.id)
            if state is None:
                state = TodayState(account_id=account.id)
                db.add(state)
            before = state.pinned_character_key
            if before == character_key:
                return PinState(character_key)

            effects.checkpoint("PRE_TODAY_PIN_CHANGE")
            state.pinned_character_key = character_key
            state.pursued_task_id = None
            state.pursued_config_version = None
            effects.record_config_change(
                account.id,
                "TODAY_PIN_CHANGED",
                "todayPin",
                before,
                character_key,
                character_key=character_key,
            )
            return PinState(character_key)
