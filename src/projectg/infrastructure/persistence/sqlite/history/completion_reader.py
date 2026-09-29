from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.domain.artifacts.quality import ArtifactQualityAdapter
from projectg.infrastructure.persistence.sqlite.artifacts.service import (artifact_fingerprint, evaluation_payload,
    latest_confirmed, load_quality_config)
from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.infrastructure.persistence.sqlite.models import (Account, SnapshotArtifact, SnapshotCharacter,
    SnapshotWeapon)
from projectg.domain.completion import CompletionResult, evaluate_completion
from projectg.domain.planning.models import CharacterState, WeaponState
from projectg.infrastructure.persistence.sqlite.repositories.targets import latest_active_targets


TALENTS = (("normal", "auto"), ("skill", "skill"), ("burst", "burst"))


def target_completion(db: Session, account: Account, snapshot_id: str | None,
                      character_key: str, target: dict,
                      quality_config: ArtifactQualityConfig | None = None) -> CompletionResult:
    if not snapshot_id:
        return evaluate_completion(None, target)
    row = db.get(SnapshotCharacter, (snapshot_id, character_key))
    if row is None:
        return evaluate_completion(None, target)
    weapon_row = (db.get(SnapshotWeapon, (snapshot_id, row.equipped_weapon_instance_id))
                  if row.equipped_weapon_instance_id else None)
    weapon = (WeaponState(weapon_row.weapon_instance_id, weapon_row.weapon_key,
                          weapon_row.level, weapon_row.ascension)
              if weapon_row else None)
    state = CharacterState(row.character_key, row.level, row.ascension,
                           {state_key: getattr(row, f"talent_{state_key}")
                            for _, state_key in TALENTS}, weapon)
    artifact = target.get("artifact", {})
    artifact_status = None
    artifact_stale = False
    if artifact.get("enabled"):
        evaluation_row = latest_confirmed(db, account.id, character_key)
        quality_config = quality_config or load_quality_config(db)
        artifacts=db.scalars(select(SnapshotArtifact).where(
            SnapshotArtifact.snapshot_id==snapshot_id,SnapshotArtifact.character_key==character_key
        ).order_by(SnapshotArtifact.slot_key,SnapshotArtifact.artifact_instance_id)).all()
        fingerprint = artifact_fingerprint(artifacts)
        state.artifact_fingerprint = fingerprint
        if evaluation_row is not None:
            if not evaluation_row.artifact_fingerprint:
                # Legacy evaluations without a loadout fingerprint cannot prove
                # which equipped artifacts their score describes.
                artifact_status = "UNKNOWN"
            else:
                evaluation = evaluation_payload(evaluation_row, fingerprint)
                result = ArtifactQualityAdapter().evaluate(
                    evaluation, artifact.get("targetQuality", "GOOD"), quality_config,
                    current_fingerprint=fingerprint)
                artifact_status = result.status.value
                artifact_stale = result.stale
        elif not quality_config.configured:
            artifact_status = "NEEDS_QUALITY_CONFIG"
    return evaluate_completion(state, target, artifact_status=artifact_status,
                               artifact_stale=artifact_stale)


def target_is_complete(db: Session, account: Account, snapshot_id: str | None,
                       character_key: str, target: dict,
                       quality_config: ArtifactQualityConfig | None = None) -> bool:
    return target_completion(db, account, snapshot_id, character_key, target,
                             quality_config).complete


def latest_targets(db: Session, account_id: str) -> dict[str, tuple[int, dict]]:
    return {key: (row.version, row.target_json)
            for key, row in latest_active_targets(db, account_id).items()}


