"""Account and snapshot lookup against the SQLite persistence models."""

from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models.entities import Account, Snapshot


class AccountRepository:
    def get_or_create(self, db: Session, account_id: str, name: str, region: str) -> Account:
        obj = db.get(Account, account_id)
        if obj is None:
            obj = next(
                (row for row in db.new if isinstance(row, Account) and row.id == account_id),
                None,
            )
        if obj is None:
            obj = Account(id=account_id, name=name, server_region=region)
            db.add(obj)
        return obj


class SnapshotRepository:
    def current(self, db: Session, account: Account) -> Snapshot | None:
        return db.get(Snapshot, account.current_snapshot_id) if account.current_snapshot_id else None
