"""Read confirmed evaluation history without choosing freshness or a winner."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from projectg.application.ports.outbound.planner_gateway import PlannerArtifactEvaluationFact
from projectg.domain.artifacts.models import EvaluationStatus
from projectg.infrastructure.persistence.sqlite.models import ArtifactEvaluation


class PlannerArtifactEvaluationReader:
    def __init__(self, db: Session):
        self._db = db

    def read(self, account_id: str) -> tuple[PlannerArtifactEvaluationFact, ...]:
        evaluation_rows = self._db.scalars(
            select(ArtifactEvaluation)
            .where(
                ArtifactEvaluation.account_id == account_id,
                ArtifactEvaluation.status == EvaluationStatus.CONFIRMED.value,
            )
            .order_by(
                ArtifactEvaluation.imported_at.desc(),
                ArtifactEvaluation.id.desc(),
            )
        ).all()
        return tuple(
            PlannerArtifactEvaluationFact(
                id=row.id,
                character_key=row.character_key,
                imported_at=row.imported_at,
                source=row.source,
                status=row.status,
                raw_metrics=dict(row.raw_metrics_json or {}),
                normalized_metrics=dict(row.normalized_metrics_json or {}),
                parser_confidence=row.parser_confidence,
                artifact_fingerprint=row.artifact_fingerprint,
            )
            for row in evaluation_rows
        )

