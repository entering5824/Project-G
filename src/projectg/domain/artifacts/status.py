from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.domain.artifacts.quality import ArtifactQualityAdapter
from projectg.domain.game_catalog.models import GameData


def build_artifact_status(
    *,
    character_key: str,
    artifact_target: dict,
    evaluation: dict | None,
    current_fingerprint: str | None,
    config: ArtifactQualityConfig,
    game: GameData,
) -> dict:
    """Evaluate artifact progress from domain values, independent of persistence rows."""
    enabled = bool(artifact_target.get("enabled"))
    result = ArtifactQualityAdapter().evaluate(
        evaluation,
        artifact_target.get("targetQuality", "GOOD"),
        config,
        current_fingerprint=current_fingerprint,
    )

    chosen_sets = [
        *(artifact_target.get("primarySets") or []),
        *(artifact_target.get("alternativeSets") or []),
    ]
    domains = []
    for set_key in dict.fromkeys(chosen_sets):
        definition = game.artifact_sets.get(set_key)
        domain = game.domains.get(definition.domain_key) if definition else None
        if domain:
            domains.append(
                {"key": domain.key, "name": domain.name or domain.key, "setKey": set_key}
            )

    return {
        "characterKey": character_key,
        "enabled": enabled,
        "status": result.status.value if enabled else "NOT_REQUIRED",
        "currentScore": result.normalized_score,
        "qualityLabel": result.quality_label,
        "target": {
            "label": artifact_target.get("targetQuality", "GOOD"),
            "score": result.target_score,
        },
        "deficiency": result.deficiency,
        "weakSlots": result.weak_slots,
        "recommendedDomain": domains[0] if domains else None,
        "candidateDomains": domains,
        "updatedAt": evaluation.get("importedAt") if evaluation else None,
        "stale": result.stale,
        "freshnessStatus": (
            "POSSIBLY_STALE"
            if result.stale
            else (
                "CURRENT"
                if evaluation
                and evaluation.get("artifactFingerprint")
                and current_fingerprint
                else "UNKNOWN"
            )
        ),
        "developerInput": result.developer_input,
        "evaluationId": evaluation.get("id") if evaluation else None,
        "evaluationStatus": evaluation.get("status") if evaluation else None,
        "qualityConfig": config.to_dict(),
        "message": result.message,
    }
