"""Account-import-specific history/completion effects within the shared SQLite UoW."""

from __future__ import annotations

from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationEffects


class AccountImportHistoryEffects:
    """Emit snapshot diff and completion transitions caused by a committed account import."""

    @staticmethod
    def record(
        effects: SqliteMutationEffects,
        account: Account,
        previous: Snapshot | None,
        current_snapshot_id: str,
    ) -> None:
        previous_id = previous.id if previous else None
        effects.persist_snapshot_diff(account.id, previous_id, current_snapshot_id)
        if previous is not None:
            effects.reconcile_completion(
                account,
                previous.id,
                current_snapshot_id,
                reason="ACCOUNT_STATE_CHANGED",
            )
