"""Versioned ArtifactEvaluation writes and persistence-facing result projection."""

from __future__ import annotations

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.artifact_exchange_gateway import ArtifactEvaluationDecision
from projectg.domain.artifacts.models import EvaluationStatus
from projectg.domain.game_catalog.models import GameData
from projectg.infrastructure.persistence.sqlite.artifacts.service import (
    artifact_status,
    evaluation_payload,
    latest_confirmed,
)
from projectg.infrastructure.persistence.sqlite.models import Account, ArtifactEvaluation


class ArtifactEvaluationWriter:
    """Persist one already-validated artifact evaluation decision."""

    @staticmethod
    def persist(
        db: Session,
        account: Account,
        decision: ArtifactEvaluationDecision,
        *,
        evaluation_id: str,
        imported_at,
    ) -> ArtifactEvaluation:
        previous = latest_confirmed(db, account.id, decision.character_key)
        if previous is not None:
            previous.status = EvaluationStatus.SUPERSEDED.value

        row = ArtifactEvaluation(
            id=evaluation_id,
            account_id=account.id,
            character_key=decision.character_key,
            imported_at=imported_at,
            source="ASSISTED_MANUAL",
            status=EvaluationStatus.CONFIRMED.value,
            raw_metrics_json=decision.metrics,
            normalized_metrics_json=decision.normalized_metrics,
            parser_confidence=1.0,
            artifact_fingerprint=decision.artifact_fingerprint,
            supersedes_id=previous.id if previous else None,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def response(
        db: Session,
        account: Account,
        row: ArtifactEvaluation,
        decision: ArtifactEvaluationDecision,
        game_data: GameData,
    ) -> dict:
        return {
            "evaluation": evaluation_payload(row, decision.artifact_fingerprint),
            "quality": artifact_status(db, account, decision.character_key, game_data),
        }
