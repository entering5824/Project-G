"""SQLite repository helpers for tier-pack versions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.domain.planning.tier_pack import blank_tier_pack
from projectg.infrastructure.persistence.sqlite.models import TierPackVersion


def current_tier_pack(db: Session, account_id: str) -> dict:
    row = db.scalar(
        select(TierPackVersion)
        .where(TierPackVersion.account_id == account_id)
        .order_by(TierPackVersion.version.desc())
        .limit(1)
    )
    if row is None:
        return {**blank_tier_pack(), "packVersion": 0}
    return {**blank_tier_pack(), **row.pack_json, "packVersion": row.version}


def append_tier_pack_version(
    db: Session,
    account_id: str,
    *,
    version: int,
    payload: dict,
) -> None:
    db.add(TierPackVersion(account_id=account_id, version=version, pack_json=payload))
