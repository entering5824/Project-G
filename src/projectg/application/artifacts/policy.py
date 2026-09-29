"""Pure application policy for previewing and validating artifact exchanges."""

from typing import Any, Iterable

from projectg.application.artifacts.errors import ArtifactExchangeError
from projectg.application.ports.outbound.artifact_document_parser import ParsedArtifactEvaluation
from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactEvaluationDecision,
    ArtifactExchangeContext,
    ArtifactExchangePreview,
)
from projectg.domain.artifacts.quality import ArtifactQualityAdapter
from projectg.domain.artifacts.validation import validate_metrics


def _require_imported_account(context: ArtifactExchangeContext) -> str:
    if not context.snapshot_id:
        raise ArtifactExchangeError(
            "Import a GOOD account before confirming an artifact evaluation."
        )
    return context.snapshot_id


def _quality(context: ArtifactExchangeContext, character_key: str, metrics: dict[str, Any]):
    character = context.characters[character_key]
    return ArtifactQualityAdapter().evaluate(
        {
            "rawMetrics": metrics,
            "artifactFingerprint": character.artifact_fingerprint,
        },
        character.target_quality,
        context.quality_config,
        current_fingerprint=character.artifact_fingerprint,
    )


def _preview_quality(context: ArtifactExchangeContext, character_key: str,
                     metrics: dict[str, Any]) -> dict[str, Any]:
    character = context.characters[character_key]
    result = _quality(context, character_key, metrics)
    return {
        "normalizedScore": result.normalized_score,
        "qualityLabel": result.quality_label,
        "qualityStatus": result.status.value,
        "targetQuality": character.target_quality,
        "targetScore": result.target_score,
        "deficiency": result.deficiency,
        "weakSlots": result.weak_slots,
        "message": result.message,
        "existingEvaluation": character.existing_evaluation,
        "artifactFingerprint": character.artifact_fingerprint,
        "targetVersion": character.target_version,
    }


def build_artifact_exchange_preview(
    parsed_rows: Iterable[ParsedArtifactEvaluation],
    context: ArtifactExchangeContext,
) -> ArtifactExchangePreview:
    snapshot_id = _require_imported_account(context)
    output: list[dict[str, Any]] = []
    for row in parsed_rows:
        errors = [dict(error) for error in row.errors]
        key = row.character_key
        if key and key not in context.owned_character_keys:
            errors.append({
                "code": "UNKNOWN_CHARACTER_KEY",
                "message": f"Unknown or unowned character key: {key}.",
            })
        quality = None
        if key in context.owned_character_keys and row.metrics:
            quality = _preview_quality(context, key, row.metrics)
        warnings: list[str] = []
        if quality and quality["message"]:
            warnings.append(quality["message"])
        if quality and quality["existingEvaluation"]:
            warnings.append(
                "A confirmed evaluation exists; this confirmation creates a new version."
            )
        output.append({
            "index": row.index,
            "characterKey": key,
            "metrics": row.metrics,
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "quality": quality,
        })
    output.sort(key=lambda item: item["index"])
    return ArtifactExchangePreview(
        snapshot_id=snapshot_id,
        evaluations=tuple(output),
        valid_count=sum(bool(item["valid"]) for item in output),
    )


def _canonical_metrics(row: dict[str, Any], index: int) -> dict[str, Any]:
    try:
        candidate = dict(row.get("metrics") or {})
    except (TypeError, ValueError) as exc:
        raise ArtifactExchangeError(
            f"Invalid artifact metrics at row {index + 1}."
        ) from exc
    if "extraMetrics" in candidate:
        candidate["extra_metrics"] = candidate.pop("extraMetrics")
    if "developerInput" in candidate:
        candidate["developer_input"] = candidate.pop("developerInput")
    try:
        return validate_metrics(candidate)
    except ValueError as exc:
        raise ArtifactExchangeError(f"INVALID_AEF_METRICS: {exc}") from exc


def prepare_artifact_exchange_commit(
    rows: Iterable[dict[str, Any]],
    preview_snapshot_id: str,
    context: ArtifactExchangeContext,
) -> tuple[ArtifactEvaluationDecision, ...]:
    snapshot_id = _require_imported_account(context)
    if preview_snapshot_id != snapshot_id:
        raise ArtifactExchangeError(
            "The account snapshot changed after preview. Preview again before confirming."
        )

    selected = list(rows)
    if not selected:
        raise ArtifactExchangeError("Select at least one valid artifact evaluation.")

    decisions: list[ArtifactEvaluationDecision] = []
    seen: set[str] = set()
    for index, row in enumerate(selected):
        key = row.get("characterKey") if isinstance(row, dict) else None
        if not isinstance(key, str) or not key.strip():
            raise ArtifactExchangeError(
                f"Invalid or duplicate character evaluation at row {index + 1}."
            )
        key = key.strip()
        if key in seen:
            raise ArtifactExchangeError(
                f"Invalid or duplicate character evaluation at row {index + 1}."
            )
        seen.add(key)
        if key not in context.owned_character_keys:
            raise ArtifactExchangeError(f"Unknown or unowned character key: {key}.")
        metrics = _canonical_metrics(row, index)
        character = context.characters[key]
        corrected = bool(row.get("manuallyCorrected", False))
        quality = _quality(context, key, metrics)
        decisions.append(ArtifactEvaluationDecision(
            character_key=key,
            metrics=metrics,
            manually_corrected=corrected,
            quality=quality,
            normalized_metrics={
                "status": quality.status.value,
                "normalizedScore": quality.normalized_score,
                "qualityLabel": quality.quality_label,
                "qualityConfigVersion": context.quality_config.version,
                "metricKey": quality.metric_key,
                "weakSlots": quality.weak_slots,
                "developerInput": quality.developer_input,
                "manuallyCorrected": corrected,
            },
            artifact_fingerprint=character.artifact_fingerprint,
            target_version=character.target_version,
        ))
    return tuple(decisions)

