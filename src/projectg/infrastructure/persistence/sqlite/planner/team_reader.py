"""Read stored team rows without inferring planner membership."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from projectg.application.ports.outbound.planner_gateway import PlannerTeamFact
from projectg.infrastructure.persistence.sqlite.models import SnapshotTeam, PlannerTeam


class PlannerTeamReader:
    def __init__(self, db: Session):
        self._db = db

    def read(self, account_id: str, snapshot_id: str) -> tuple[PlannerTeamFact, ...]:
        snapshot = self._db.scalars(select(SnapshotTeam).where(
            SnapshotTeam.snapshot_id == snapshot_id)).all()
        configured = self._db.scalars(select(PlannerTeam).where(
            PlannerTeam.account_id == account_id)).all()
        return (
            *(PlannerTeamFact(tuple(row.members_json or [])) for row in snapshot),
            *(PlannerTeamFact(tuple(row.members_json or []), row.is_primary) for row in configured),
        )
