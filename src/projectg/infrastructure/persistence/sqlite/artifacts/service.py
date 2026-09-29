import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import (
    Account, ArtifactEvaluation, ArtifactQualityConfigVersion,
    SnapshotArtifact, SnapshotCharacter, SnapshotWeapon,
)
from projectg.infrastructure.persistence.sqlite.repositories.targets import latest_active_targets
from projectg.domain.planning.models import CharacterState, WeaponState
from projectg.domain.game_catalog.models import GameData

from projectg.domain.artifacts.models import ArtifactQualityConfig, EvaluationStatus
from projectg.domain.artifacts.validation import validate_metrics, validate_quality_config
from projectg.domain.artifacts.status import build_artifact_status

DEFAULT_ARTIFACT_QUALITY_CONFIG = ArtifactQualityConfig()


def load_quality_config(db: Session) -> ArtifactQualityConfig:
    row = db.scalar(select(ArtifactQualityConfigVersion).order_by(ArtifactQualityConfigVersion.version.desc()).limit(1))
    return validate_quality_config(row.config_json, row.version) if row else DEFAULT_ARTIFACT_QUALITY_CONFIG


def save_quality_config(db: Session, payload: dict) -> ArtifactQualityConfig:
    current = db.scalar(select(func.max(ArtifactQualityConfigVersion.version))) or 0
    config = validate_quality_config(payload, int(current) + 1)
    db.add(ArtifactQualityConfigVersion(version=config.version, config_json={
        "adapterType": config.adapter_type, "thresholds": config.thresholds,
    }))
    db.flush()
    return config


def latest_confirmed(db: Session, account_id: str, character_key: str):
    return db.scalar(select(ArtifactEvaluation).where(
        ArtifactEvaluation.account_id == account_id,
        ArtifactEvaluation.character_key == character_key,
        ArtifactEvaluation.status == EvaluationStatus.CONFIRMED.value,
    ).order_by(ArtifactEvaluation.imported_at.desc(), ArtifactEvaluation.id.desc()).limit(1))


def evaluation_payload(row: ArtifactEvaluation, current_fingerprint: str | None = None) -> dict:
    stale = bool(row.artifact_fingerprint and row.artifact_fingerprint != current_fingerprint)
    freshness = "POSSIBLY_STALE" if stale else ("CURRENT" if row.artifact_fingerprint and current_fingerprint else "UNKNOWN")
    return {"id": row.id, "characterKey": row.character_key, "importedAt": row.imported_at.isoformat(),
            "source": row.source, "status": row.status, "rawMetrics": row.raw_metrics_json,
            "normalizedMetrics": row.normalized_metrics_json, "parserConfidence": row.parser_confidence,
            "artifactFingerprint": row.artifact_fingerprint, "stale": stale, "freshnessStatus": freshness}


def current_artifact_fingerprint(db: Session, account: Account, character_key: str) -> str | None:
    if not account.current_snapshot_id:
        return None
    rows = db.scalars(select(SnapshotArtifact).where(
        SnapshotArtifact.snapshot_id == account.current_snapshot_id,
        SnapshotArtifact.character_key == character_key).order_by(SnapshotArtifact.slot_key, SnapshotArtifact.artifact_instance_id)).all()
    return artifact_fingerprint(rows)


def artifact_fingerprint(rows: list[SnapshotArtifact]) -> str | None:
    if not rows:
        return None
    content = [{
        "id": row.artifact_instance_id,
        "set": row.set_key,
        "slot": row.slot_key,
        "rarity": row.rarity,
        "level": row.level,
        "mainStat": row.main_stat_key,
        "substats": row.substats_json or [],
        "unactivatedSubstats": row.unactivated_substats_json or [],
    } for row in rows]
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def artifact_fingerprints_for_snapshot(db: Session, snapshot_id: str | None) -> dict[str, str | None]:
    if not snapshot_id:
        return {}
    grouped: dict[str, list[SnapshotArtifact]] = {}
    rows = db.scalars(select(SnapshotArtifact).where(SnapshotArtifact.snapshot_id == snapshot_id)
                      .order_by(SnapshotArtifact.character_key, SnapshotArtifact.slot_key,
                                SnapshotArtifact.artifact_instance_id)).all()
    for row in rows:
        grouped.setdefault(row.character_key, []).append(row)
    return {key:artifact_fingerprint(items) for key, items in grouped.items()}


def character_state(db: Session, account: Account, character_key: str) -> CharacterState | None:
    if not account.current_snapshot_id:
        return None
    row = db.get(SnapshotCharacter, (account.current_snapshot_id, character_key))
    if row is None:
        return None
    weapon_row = db.get(SnapshotWeapon, (account.current_snapshot_id, row.equipped_weapon_instance_id)) if row.equipped_weapon_instance_id else None
    weapon = WeaponState(weapon_row.weapon_instance_id, weapon_row.weapon_key, weapon_row.level, weapon_row.ascension) if weapon_row else None
    return CharacterState(character_key, row.level, row.ascension,
        {"auto": row.talent_auto, "skill": row.talent_skill, "burst": row.talent_burst}, weapon,
        current_artifact_fingerprint(db, account, character_key))


def target_for(db: Session, account_id: str, character_key: str):
    return latest_active_targets(db, account_id).get(character_key)


def artifact_status_from_records(account: Account, character_key: str, target_row,
                                 row: ArtifactEvaluation | None, current: str | None,
                                 config: ArtifactQualityConfig, game: GameData) -> dict:
    target = target_row.target_json.get("artifact", {}) if target_row else {}
    evaluation = evaluation_payload(row, current) if row else None
    return build_artifact_status(
        character_key=character_key,
        artifact_target=target,
        evaluation=evaluation,
        current_fingerprint=current,
        config=config,
        game=game,
    )


def artifact_status(db: Session, account: Account, character_key: str,
                    game: GameData) -> dict:
    target_row = target_for(db, account.id, character_key)
    row = latest_confirmed(db, account.id, character_key)
    current = current_artifact_fingerprint(db, account, character_key)
    config = load_quality_config(db)
    return artifact_status_from_records(account, character_key, target_row, row, current, config, game)
