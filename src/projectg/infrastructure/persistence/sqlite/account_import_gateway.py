"""SQLite facade for loading and persisting validated account imports."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from projectg.application.imports.errors import ConcurrentAccountImportError
from projectg.application.ports.outbound.account_import_gateway import (
    AccountImportCommit,
    AccountImportCommitCommand,
    AccountImportContext,
)
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import (
    AccountImportContextReader,
    AccountImportHistoryEffects,
    AccountSnapshotWriter,
)
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqliteAccountImportGateway:
    """Coordinate account-import persistence primitives inside one recovery-safe transaction."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        context_reader: AccountImportContextReader,
        raw_storage: AccountImportRawDocumentStorage,
        mutation_uow: SqliteMutationUnitOfWork,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._context = context_reader
        self._raw_storage = raw_storage
        self._mutations = mutation_uow

    def load_context(self) -> AccountImportContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                return self._context.load(db)

    def commit_validated(self, command: AccountImportCommitCommand) -> AccountImportCommit:
        path = self._raw_storage.write(
            command.imported_at,
            command.document.raw_hash,
            command.document.raw_content,
        )
        previous_id: str | None = None
        try:
            with self._mutations.transaction() as effects:
                db = effects.db
                account = self._context.account(db)
                if account.current_snapshot_id != command.expected_previous_snapshot_id:
                    raise ConcurrentAccountImportError(
                        "The account snapshot changed while the import was being prepared."
                    )
                previous = self._context.current_snapshot(db, account)
                previous_id = previous.id if previous else None
                effects.checkpoint("PRE_GOOD_IMPORT")
                AccountSnapshotWriter.persist(db, account, previous, command, path)
                AccountImportHistoryEffects.record(effects, account, previous, command.snapshot_id)
        except Exception:
            self._raw_storage.delete(path)
            raise
        return AccountImportCommit(
            snapshot_id=command.snapshot_id,
            previous_snapshot_id=previous_id,
        )
