"""SQLite storage mechanics for target-import idempotency receipts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import IdempotencyReceipt


class TargetIdempotencyRepository:
    @staticmethod
    def fingerprint(payload: object, selected_keys: set[str]) -> str:
        payload_json = json.dumps(
            {"payload": payload, "selected": sorted(selected_keys)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    @staticmethod
    def get(db: Session, account_id: str, operation_id: str) -> IdempotencyReceipt | None:
        return db.get(IdempotencyReceipt, (account_id, operation_id))

    @staticmethod
    def response(receipt: IdempotencyReceipt) -> dict:
        return deepcopy(receipt.response_json)

    @staticmethod
    def store(
        db: Session,
        *,
        account_id: str,
        operation_id: str,
        payload_hash: str,
        response: dict,
    ) -> None:
        db.add(
            IdempotencyReceipt(
                account_id=account_id,
                request_key=operation_id,
                payload_hash=payload_hash,
                response_json=deepcopy(response),
            )
        )
