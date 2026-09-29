"""SQLite adapter for configured and observed teams."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.teams_gateway import TeamsData
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import PlannerTeam, SnapshotCharacter, SnapshotTeam
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqliteTeamsGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        mutation_uow: SqliteMutationUnitOfWork,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration
        self._mutations = mutation_uow

    def load(self) -> TeamsData:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                return self._load_data(db, self._account(db))

    def commit_validated(self, rows: list[dict[str, Any]]) -> TeamsData:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._account(db)
            existing = db.scalars(
                select(PlannerTeam).where(PlannerTeam.account_id == account.id)
            ).all()
            before = [
                {
                    "teamId": row.team_id,
                    "name": row.name,
                    "members": row.members_json,
                    "isPrimary": bool(row.is_primary),
                }
                for row in sorted(existing, key=lambda item: item.team_id)
            ]
            if before == rows:
                return self._load_data(db, account)

            effects.checkpoint("PRE_TEAM_CONFIG_CHANGE")
            for row in existing:
                db.delete(row)
            db.flush()
            for row in rows:
                db.add(PlannerTeam(
                    account_id=account.id,
                    team_id=row["teamId"],
                    name=row["name"],
                    members_json=row["members"],
                    is_primary=row["isPrimary"],
                ))
            effects.record_config_change(
                account.id,
                "TEAM_CONFIG_CHANGED",
                "plannerTeams",
                before,
                rows,
            )
            db.flush()
            return self._load_data(db, account)

    def _account(self, db: Session):
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    @staticmethod
    def _load_data(db: Session, account) -> TeamsData:
        owned: list[str] = []
        imported: list[dict[str, Any]] = []
        if account.current_snapshot_id:
            owned = list(db.scalars(
                select(SnapshotCharacter.character_key)
                .where(SnapshotCharacter.snapshot_id == account.current_snapshot_id)
                .order_by(SnapshotCharacter.character_key)
            ))
            imported = [
                {
                    "teamId": row.team_id,
                    "name": row.name or row.team_id,
                    "members": row.members_json,
                }
                for row in db.scalars(
                    select(SnapshotTeam)
                    .where(SnapshotTeam.snapshot_id == account.current_snapshot_id)
                    .order_by(SnapshotTeam.team_id)
                ).all()
            ]
        configured = [
            {
                "teamId": row.team_id,
                "name": row.name,
                "members": row.members_json,
                "isPrimary": bool(row.is_primary),
            }
            for row in db.scalars(
                select(PlannerTeam)
                .where(PlannerTeam.account_id == account.id)
                .order_by(PlannerTeam.team_id)
            ).all()
        ]
        return TeamsData(
            owned_characters=tuple(owned),
            imported_teams=tuple(imported),
            configured_teams=tuple(configured),
        )
