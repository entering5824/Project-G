"""Artifact-exchange-specific history/completion effects within the shared SQLite UoW."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.artifact_exchange_gateway import ArtifactEvaluationDecision
from projectg.infrastructure.persistence.sqlite.artifacts.service import latest_confirmed
from projectg.infrastructure.persistence.sqlite.history.completion_reader import latest_targets, target_is_complete
from projectg.infrastructure.persistence.sqlite.models import Account, ArtifactEvaluation
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationEffects


@dataclass(frozen=True)
class ArtifactEvaluationBaseline:
    previous_evaluation_id: str | None
    target_record: tuple[int, dict] | None
    was_complete: bool


class ArtifactExchangeHistoryEffects:
    """Capture completion baseline and emit artifact-specific history transitions."""

    @staticmethod
    def capture(db: Session, account: Account, character_key: str) -> ArtifactEvaluationBaseline:
        previous = latest_confirmed(db, account.id, character_key)
        target_record = latest_targets(db, account.id).get(character_key)
        was_complete = bool(
            target_record
            and target_is_complete(
                db,
                account,
                account.current_snapshot_id,
                character_key,
                target_record[1],
            )
        )
        return ArtifactEvaluationBaseline(
            previous_evaluation_id=previous.id if previous else None,
            target_record=target_record,
            was_complete=was_complete,
        )

    @staticmethod
    def record(
        effects: SqliteMutationEffects,
        account: Account,
        decision: ArtifactEvaluationDecision,
        row: ArtifactEvaluation,
        baseline: ArtifactEvaluationBaseline,
    ) -> None:
        key = decision.character_key
        quality = decision.quality
        effects.record_event(
            account.id,
            "DERIVED",
            "ARTIFACT_EVALUATION_CHANGED",
            {
                "evaluationId": row.id,
                "previousEvaluationId": baseline.previous_evaluation_id,
                "currentScore": quality.normalized_score,
                "currentLabel": quality.quality_label,
                "source": "ASSISTED_MANUAL",
                "manuallyCorrected": decision.manually_corrected,
            },
            character_key=key,
        )

        target_record = baseline.target_record
        is_complete = bool(
            target_record
            and quality.status.value == "COMPLETE"
            and target_is_complete(
                effects.db,
                account,
                account.current_snapshot_id,
                key,
                target_record[1],
            )
        )
        quality_config_version = decision.normalized_metrics["qualityConfigVersion"]
        if not baseline.was_complete and is_complete:
            effects.record_event(
                account.id,
                "DERIVED",
                "ARTIFACT_TARGET_REACHED",
                {
                    "evaluationId": row.id,
                    "targetVersion": target_record[0],
                    "artifactQualityConfigVersion": quality_config_version,
                    "currentScore": quality.normalized_score,
                    "targetScore": quality.target_score,
                },
                character_key=key,
            )
            effects.record_event(
                account.id,
                "DERIVED",
                "CHARACTER_COMPLETED",
                {
                    "reason": "TARGET_REACHED",
                    "targetVersion": target_record[0],
                    "artifactQualityConfigVersion": quality_config_version,
                    "completionDependsOn": {
                        "snapshotId": account.current_snapshot_id,
                        "targetVersion": target_record[0],
                        "artifactQualityConfigVersion": quality_config_version,
                    },
                },
                snapshot_id=account.current_snapshot_id,
                character_key=key,
            )
        elif baseline.was_complete and not is_complete:
            effects.record_event(
                account.id,
                "DERIVED",
                "CHARACTER_REOPENED",
                {
                    "reason": "ARTIFACT_EVALUATION_CHANGED",
                    "targetVersion": target_record[0] if target_record else None,
                    "artifactQualityConfigVersion": quality_config_version,
                },
                snapshot_id=account.current_snapshot_id,
                character_key=key,
            )
