"""Transaction-scoped SQLite mutation effects.

This module centralizes cross-cutting mutation mechanics that must share the same
SQLAlchemy transaction as a bounded-context write: pre-mutation backups,
history-event persistence, completion reconciliation, snapshot diffs, and
commit/rollback.

Concrete gateways still own their bounded-context row mutations. They do not
own transaction finalization or cross-cutting effects.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.infrastructure.persistence.sqlite.history.completion_reader import latest_targets, target_is_complete
from projectg.infrastructure.persistence.sqlite.history.events import record_event
from projectg.infrastructure.persistence.sqlite.history.snapshots import persist_snapshot_diff
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.artifacts.service import load_quality_config


@contextmanager
def finalize_existing_transaction(db: Session) -> Iterator[Session]:
    """Commit/rollback an already-open persistence session at one boundary."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


class SqliteMutationEffects:
    """Cross-cutting effects bound to one open SQLite transaction."""

    def __init__(self, db: Session, backup_service, clock: Clock | None, id_generator: IdGenerator | None):
        self.db = db
        self._backup_service = backup_service
        self._clock = clock
        self._id_generator = id_generator

    def checkpoint(self, reason: str) -> None:
        """Create at most one automatic recovery checkpoint per transaction."""
        self._backup_service.before_mutation(self.db, reason)

    def now(self):
        if self._clock is None:
            raise RuntimeError("This mutation scope has no clock port.")
        return self._clock.now()

    def next_id(self) -> str:
        if self._id_generator is None:
            raise RuntimeError("This mutation scope has no ID generator port.")
        return self._id_generator.next_id()

    def record_event(
        self,
        account_id: str,
        source: str,
        event_type: str,
        payload: dict,
        *,
        snapshot_id: str | None = None,
        character_key: str | None = None,
        created_at=None,
    ):
        if self._clock is None or self._id_generator is None:
            raise RuntimeError("History effects require clock and ID generator ports.")
        return record_event(
            self.db,
            account_id,
            source,
            event_type,
            payload,
            snapshot_id=snapshot_id,
            character_key=character_key,
            created_at=created_at,
            clock=self._clock,
            id_generator=self._id_generator,
        )

    def record_config_change(
        self,
        account_id: str,
        event_type: str,
        entity_key: str,
        before: Any,
        after: Any,
        *,
        character_key: str | None = None,
        versions: dict | None = None,
    ):
        if before == after:
            return None
        return self.record_event(
            account_id,
            "CONFIG",
            event_type,
            {
                "entityKey": entity_key,
                "before": before,
                "after": after,
                "versions": versions or {},
            },
            character_key=character_key,
        )

    def reconcile_completion(
        self,
        account,
        before_snapshot_id: str | None,
        after_snapshot_id: str | None,
        *,
        reason: str,
        before_targets: dict[str, tuple[int, dict]] | None = None,
        after_targets: dict[str, tuple[int, dict]] | None = None,
        before_quality_config: ArtifactQualityConfig | None = None,
        after_quality_config: ArtifactQualityConfig | None = None,
    ) -> None:
        if self._clock is None or self._id_generator is None:
            raise RuntimeError("Completion effects require clock and ID generator ports.")
        before_targets = (
            before_targets if before_targets is not None else latest_targets(self.db, account.id)
        )
        after_targets = (
            after_targets if after_targets is not None else latest_targets(self.db, account.id)
        )
        for key in sorted(before_targets.keys() | after_targets.keys()):
            previous = before_targets.get(key)
            current = after_targets.get(key)
            was_complete = bool(
                previous
                and target_is_complete(
                    self.db, account, before_snapshot_id, key, previous[1], before_quality_config
                )
            )
            is_complete = bool(
                current
                and target_is_complete(
                    self.db, account, after_snapshot_id, key, current[1], after_quality_config
                )
            )
            if was_complete == is_complete:
                continue
            event_type = "CHARACTER_COMPLETED" if is_complete else "CHARACTER_REOPENED"
            quality = after_quality_config or load_quality_config(self.db)
            payload = {
                "reason": (
                    reason
                    if event_type == "CHARACTER_REOPENED" or reason.endswith("CHANGED")
                    else "TARGET_REACHED"
                ),
                "targetVersion": current[0] if current else None,
                "previousTargetVersion": previous[0] if previous else None,
                "artifactQualityConfigVersion": quality.version,
                "completionDependsOn": {
                    "snapshotId": after_snapshot_id,
                    "targetVersion": current[0] if current else None,
                    "artifactQualityConfigVersion": quality.version,
                },
            }
            self.record_event(
                account.id,
                "DERIVED",
                event_type,
                payload,
                snapshot_id=after_snapshot_id,
                character_key=key,
            )

    def persist_snapshot_diff(
        self,
        account_id: str,
        from_snapshot_id: str | None,
        to_snapshot_id: str,
    ):
        if self._clock is None or self._id_generator is None:
            raise RuntimeError("Snapshot-history effects require clock and ID generator ports.")
        return persist_snapshot_diff(
            self.db,
            account_id,
            from_snapshot_id,
            to_snapshot_id,
            clock=self._clock,
            id_generator=self._id_generator,
        )


class SqliteMutationUnitOfWork:
    """Open and finalize transaction-scoped mutation effects."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        backup_service,
        clock: Clock | None = None,
        id_generator: IdGenerator | None = None,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._backup_service = backup_service
        self._clock = clock
        self._id_generator = id_generator

    @contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[SqliteMutationEffects]:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                if immediate and not db.in_transaction():
                    db.connection(execution_options={"sqlite_begin_mode": "IMMEDIATE"})
                effects = SqliteMutationEffects(
                    db,
                    self._backup_service,
                    self._clock,
                    self._id_generator,
                )
                try:
                    yield effects
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
