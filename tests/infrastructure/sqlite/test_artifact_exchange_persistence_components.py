from datetime import datetime, timezone

from projectg.application.ports.outbound.artifact_exchange_gateway import ArtifactEvaluationDecision
from projectg.domain.artifacts.models import ArtifactQualityResult, EvaluationStatus, QualityStatus
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.artifact_exchange.context_reader import (
    ArtifactExchangeContextReader,
)
from projectg.infrastructure.persistence.sqlite.artifact_exchange.evaluation_writer import (
    ArtifactEvaluationWriter,
)
from projectg.infrastructure.persistence.sqlite.artifact_exchange.history_effects import (
    ArtifactExchangeHistoryEffects,
)
from projectg.infrastructure.persistence.sqlite.models import Account, ArtifactEvaluation


def _decision() -> ArtifactEvaluationDecision:
    return ArtifactEvaluationDecision(
        character_key="Fischl",
        metrics={"rv": 250},
        manually_corrected=False,
        quality=ArtifactQualityResult(
            status=QualityStatus.NEEDS_QUALITY_CONFIG,
            normalized_score=250.0,
            quality_label=None,
            target_score=None,
            deficiency=None,
        ),
        normalized_metrics={"rv": 250.0, "qualityConfigVersion": 0},
        artifact_fingerprint="fp-new",
        target_version=None,
    )


def test_artifact_context_reader_returns_empty_context_without_snapshot(db_session):
    reader = ArtifactExchangeContextReader(Settings(account_id="artifact-test"))

    context = reader.load(db_session)

    assert context.snapshot_id is None
    assert context.owned_character_keys == frozenset()
    assert context.characters == {}
    assert context.quality_config.version == 0


def test_artifact_evaluation_writer_supersedes_previous_confirmed_row(db_session):
    account = Account(id="default", name="Default", server_region="NA")
    previous = ArtifactEvaluation(
        id="old",
        account_id=account.id,
        character_key="Fischl",
        imported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="ASSISTED_MANUAL",
        status=EvaluationStatus.CONFIRMED.value,
        raw_metrics_json={"rv": 100},
        normalized_metrics_json={"rv": 100, "qualityConfigVersion": 0},
        parser_confidence=1.0,
        artifact_fingerprint="fp-old",
        supersedes_id=None,
    )
    db_session.add_all([account, previous])
    db_session.flush()

    row = ArtifactEvaluationWriter.persist(
        db_session,
        account,
        _decision(),
        evaluation_id="new",
        imported_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert previous.status == EvaluationStatus.SUPERSEDED.value
    assert row.status == EvaluationStatus.CONFIRMED.value
    assert row.supersedes_id == "old"
    assert row.artifact_fingerprint == "fp-new"


def test_artifact_history_baseline_capture_is_read_only(db_session):
    account = Account(id="default", name="Default", server_region="NA")
    previous = ArtifactEvaluation(
        id="old",
        account_id=account.id,
        character_key="Fischl",
        imported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="ASSISTED_MANUAL",
        status=EvaluationStatus.CONFIRMED.value,
        raw_metrics_json={"rv": 100},
        normalized_metrics_json={"rv": 100, "qualityConfigVersion": 0},
        parser_confidence=1.0,
        artifact_fingerprint="fp-old",
        supersedes_id=None,
    )
    db_session.add_all([account, previous])
    db_session.flush()

    baseline = ArtifactExchangeHistoryEffects.capture(db_session, account, "Fischl")

    assert baseline.previous_evaluation_id == "old"
    assert baseline.target_record is None
    assert baseline.was_complete is False
    assert previous.status == EvaluationStatus.CONFIRMED.value
