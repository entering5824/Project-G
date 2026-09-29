"""Technical provenance hashing for persisted planner runs.

This adapter intentionally owns deterministic serialization/file hashing. It does
not score plans, summarize feedback, or make planner decisions.
"""

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG, config_payload
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    ArtifactEvaluation,
    ArtifactQualityConfigVersion,
    CharacterPriority,
    SnapshotArtifact,
    SnapshotCharacter,
    SnapshotWeapon,
    TierAssignmentVersion,
    TierConfigVersion,
)
from projectg.infrastructure.persistence.sqlite.planner_config import latest_config_row, load_config
from projectg.infrastructure.persistence.sqlite.repositories.targets import latest_active_targets
from projectg.infrastructure.persistence.sqlite.repositories.tier_pack import current_tier_pack
from projectg.infrastructure.serialization.tier_pack_digest import tier_pack_hash


ENGINE_VERSION = DEFAULT_PLANNER_CONFIG.planner_version


def _file_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _canonical_hash(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PlannerProvenance:
    def __init__(self, db: Session, configuration: Settings, game_data: GameData):
        self._db = db
        self._configuration = configuration
        self._game_data = game_data
        self._dataset_hashes: dict | None = None

    def dataset_hashes(self) -> dict:
        if self._dataset_hashes is not None:
            return dict(self._dataset_hashes)

        account = self._db.get(Account, self._configuration.account_id)
        account_id = account.id if account else self._configuration.account_id
        snapshot_id = account.current_snapshot_id if account else None
        observed = {}
        if snapshot_id:
            observed = {
                "characters": [
                    {
                        "key": row.character_key,
                        "level": row.level,
                        "ascension": row.ascension,
                        "constellation": row.constellation,
                        "talents": [row.talent_auto, row.talent_skill, row.talent_burst],
                    }
                    for row in self._db.scalars(
                        select(SnapshotCharacter)
                        .where(SnapshotCharacter.snapshot_id == snapshot_id)
                        .order_by(SnapshotCharacter.character_key)
                    )
                ],
                "weapons": [
                    {
                        "id": row.weapon_instance_id,
                        "key": row.weapon_key,
                        "level": row.level,
                        "ascension": row.ascension,
                    }
                    for row in self._db.scalars(
                        select(SnapshotWeapon)
                        .where(SnapshotWeapon.snapshot_id == snapshot_id)
                        .order_by(SnapshotWeapon.weapon_instance_id)
                    )
                ],
                "artifacts": [
                    {
                        "id": row.artifact_instance_id,
                        "character": row.character_key,
                        "set": row.set_key,
                        "slot": row.slot_key,
                        "mainStat": row.main_stat_key,
                        "rv": row.rv,
                    }
                    for row in self._db.scalars(
                        select(SnapshotArtifact)
                        .where(SnapshotArtifact.snapshot_id == snapshot_id)
                        .order_by(SnapshotArtifact.artifact_instance_id)
                    )
                ],
            }

        tier_pack = current_tier_pack(self._db, account_id)
        value = {
            "snapshotId": snapshot_id,
            "snapshotHash": _canonical_hash(observed) if snapshot_id else None,
            "tierPackVersion": tier_pack["packVersion"],
            "tierPackHash": tier_pack_hash(tier_pack),
            "buildKnowledgeHash": _file_hash(self._configuration.build_profiles_path),
            "gameDataHash": _file_hash(self._configuration.game_data_path),
            "plannerConfigHash": _canonical_hash(config_payload(load_config(self._db))),
        }
        self._dataset_hashes = value
        return dict(value)

    def context_hash(self) -> str:
        account = self._db.get(Account, self._configuration.account_id)
        account_id = account.id if account else self._configuration.account_id
        current_targets = {
            key: {
                "version": row.version,
                "presetKey": row.preset_key,
                "target": row.target_json,
            }
            for key, row in latest_active_targets(self._db, account_id).items()
        }
        assignments = self._db.scalars(
            select(TierAssignmentVersion)
            .where(TierAssignmentVersion.account_id == account_id)
            .order_by(
                TierAssignmentVersion.character_key,
                TierAssignmentVersion.version.desc(),
            )
        ).all()
        current_assignments = {}
        for row in assignments:
            current_assignments.setdefault(
                row.character_key,
                {"version": row.version, "tierKey": row.tier_key},
            )
        tier = self._db.scalar(
            select(TierConfigVersion)
            .order_by(TierConfigVersion.version.desc())
            .limit(1)
        )
        priorities = self._db.scalars(
            select(CharacterPriority)
            .where(CharacterPriority.account_id == account_id)
            .order_by(CharacterPriority.character_key)
        ).all()
        config = latest_config_row(self._db)
        artifact_quality = self._db.scalar(
            select(ArtifactQualityConfigVersion)
            .order_by(ArtifactQualityConfigVersion.version.desc())
            .limit(1)
        )
        evaluations = self._db.scalars(
            select(ArtifactEvaluation)
            .where(
                ArtifactEvaluation.account_id == account_id,
                ArtifactEvaluation.status == "CONFIRMED",
            )
            .order_by(
                ArtifactEvaluation.character_key,
                ArtifactEvaluation.imported_at.desc(),
                ArtifactEvaluation.id.desc(),
            )
        ).all()
        latest_evaluations = {}
        for row in evaluations:
            latest_evaluations.setdefault(
                row.character_key,
                {
                    "id": row.id,
                    "fingerprint": row.artifact_fingerprint,
                    "raw": row.raw_metrics_json,
                },
            )

        context = {
            "accountId": account_id,
            "snapshotId": account.current_snapshot_id if account else None,
            "targets": current_targets,
            "tierConfig": (
                {"version": tier.version, "tiers": tier.tiers_json}
                if tier
                else None
            ),
            "tierAssignments": current_assignments,
            "priorityOverrides": {
                row.character_key: row.override for row in priorities
            },
            "plannerConfigVersion": config.version if config else 1,
            "plannerEngineVersion": ENGINE_VERSION,
            "artifactQualityConfigVersion": (
                artifact_quality.version if artifact_quality else 0
            ),
            "artifactEvaluations": latest_evaluations,
            "gameDataVersion": self._game_data.metadata.get("data_version"),
            "datasetHashes": self.dataset_hashes(),
        }
        return _canonical_hash(context)
