from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.infrastructure.persistence.sqlite.models import HistoryEvent


def record_event(
    db: Session,
    account_id: str,
    source: str,
    event_type: str,
    payload: dict,
    *,
    snapshot_id: str | None = None,
    character_key: str | None = None,
    created_at: datetime | None = None,
    clock: Clock,
    id_generator: IdGenerator,
) -> HistoryEvent:
    if source not in {"SNAPSHOT", "CONFIG", "DERIVED"}:
        raise ValueError(f"Invalid history event source: {source}")
    row = HistoryEvent(
        id=id_generator.next_id(),
        account_id=account_id,
        created_at=created_at or clock.now(),
        source=source,
        event_type=event_type,
        snapshot_id=snapshot_id,
        character_key=character_key,
        payload_json=payload,
    )
    db.add(row)
    return row
