"""SQLite facade for versioned artifact evaluation persistence."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from projectg.application.artifacts.errors import ArtifactExchangeError
from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactExchangeCommit,
    ArtifactExchangeCommitCommand,
    ArtifactExchangeContext,
    ArtifactExchangeGateway,
)
from projectg.domain.game_catalog.models import GameData
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.artifact_exchange import (
    ArtifactEvaluationWriter,
    ArtifactExchangeContextReader,
    ArtifactExchangeHistoryEffects,
)
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class SqliteArtifactExchangeGateway(ArtifactExchangeGateway):
    """Coordinate validated artifact decisions over small SQLite primitives."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        mutation_uow: SqliteMutationUnitOfWork,
        game_data: GameData,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._game_data = game_data
        self._mutations = mutation_uow
        self._context = ArtifactExchangeContextReader(configuration)
        self._writer = ArtifactEvaluationWriter()
        self._history = ArtifactExchangeHistoryEffects()

    def load_context(self) -> ArtifactExchangeContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                return self._context.load(db)

    def commit_validated(self, command: ArtifactExchangeCommitCommand) -> ArtifactExchangeCommit:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._context.account(db)
            if not account.current_snapshot_id:
                raise ArtifactExchangeError(
                    "Import a GOOD account before confirming an artifact evaluation."
                )
            if command.expected_snapshot_id != account.current_snapshot_id:
                raise ArtifactExchangeError(
                    "The account snapshot changed after preview. Preview again before confirming."
                )
            if not command.evaluations:
                raise ArtifactExchangeError("Select at least one valid artifact evaluation.")

            owned = self._context.owned_character_keys(db, account.current_snapshot_id)
            unknown = [
                item.character_key for item in command.evaluations if item.character_key not in owned
            ]
            if unknown:
                raise ArtifactExchangeError(f"Unknown or unowned character key: {unknown[0]}.")

            effects.checkpoint("PRE_ARTIFACT_EVALUATION_IMPORT")
            results = []
            for decision in command.evaluations:
                baseline = self._history.capture(db, account, decision.character_key)
                row = self._writer.persist(
                    db,
                    account,
                    decision,
                    evaluation_id=effects.next_id(),
                    imported_at=effects.now(),
                )
                self._history.record(effects, account, decision, row, baseline)
                results.append(self._writer.response(db, account, row, decision, self._game_data))
            return ArtifactExchangeCommit(tuple(results))
