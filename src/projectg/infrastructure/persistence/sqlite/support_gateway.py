"""SQLite/filesystem adapter for support facts and maintenance operations."""

from collections.abc import Callable
from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.support_gateway import (
    HistoryContext,
    HistoryEventFact,
    HistorySnapshotFact,
    LogDirectory,
    SupportData,
)
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.history.snapshots import compare_snapshots, snapshot_index
from projectg.infrastructure.persistence.sqlite.models import Account, HistoryEvent, Snapshot
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class SqliteSupportGateway:
    def __init__(self, session_factory: Callable[[], Session],
                 maintenance_gate: DatabaseMaintenanceGate, configuration: Settings):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration

    def load_history(self, limit: int) -> HistoryContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = db.get(Account, self._configuration.account_id)
                if account is None:
                    return HistoryContext((), (), None)

                snapshot_rows = db.scalars(
                    select(Snapshot)
                    .where(Snapshot.account_id == account.id)
                    .order_by(Snapshot.imported_at.desc(), Snapshot.id.desc())
                    .limit(limit)
                ).all()
                snapshots = tuple(HistorySnapshotFact(
                    id=row.id,
                    when=row.imported_at.isoformat(),
                    current=row.id == account.current_snapshot_id,
                    previous_snapshot_id=row.previous_snapshot_id,
                    snapshot_index=snapshot_index(db, account.id, row.id),
                ) for row in snapshot_rows)

                event_rows = db.scalars(
                    select(HistoryEvent)
                    .where(HistoryEvent.account_id == account.id)
                    .order_by(HistoryEvent.created_at.desc(), HistoryEvent.id.desc())
                    .limit(limit)
                ).all()
                events = tuple(HistoryEventFact(
                    id=row.id,
                    when=row.created_at.isoformat(),
                    source=row.source,
                    event=row.event_type,
                    character=row.character_key,
                    snapshot_id=row.snapshot_id,
                    payload=row.payload_json,
                ) for row in event_rows)
                return HistoryContext(snapshots, events, account.current_snapshot_id)

    def compare_history(self, from_snapshot_id: str, to_snapshot_id: str) -> SupportData:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = db.get(Account, self._configuration.account_id)
                if account is None:
                    raise LookupError("No local account is available.")
                before = db.get(Snapshot, from_snapshot_id)
                after = db.get(Snapshot, to_snapshot_id)
                if (
                    before is None
                    or after is None
                    or before.account_id != account.id
                    or after.account_id != account.id
                ):
                    raise LookupError("Snapshot not found for this account.")
                return SupportData(compare_snapshots(db, from_snapshot_id, to_snapshot_id))

    def logs_directory(self) -> LogDirectory:
        self._configuration.log_dir.mkdir(parents=True, exist_ok=True)
        return LogDirectory(str(self._configuration.log_dir))
