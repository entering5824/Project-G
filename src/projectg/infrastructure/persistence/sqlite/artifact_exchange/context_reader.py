"""Read-only SQLite facts used by artifact exchange workflows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactCharacterContext,
    ArtifactExchangeContext,
)
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.artifacts.service import (
    current_artifact_fingerprint,
    latest_confirmed,
    load_quality_config,
)
from projectg.infrastructure.persistence.sqlite.history.completion_reader import latest_targets
from projectg.infrastructure.persistence.sqlite.models import Account, SnapshotCharacter
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository


class ArtifactExchangeContextReader:
    """Translate SQLite account/artifact rows into application-facing facts."""

    def __init__(self, configuration: Settings):
        self._configuration = configuration

    def account(self, db: Session) -> Account:
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    @staticmethod
    def owned_character_keys(db: Session, snapshot_id: str | None) -> frozenset[str]:
        if not snapshot_id:
            return frozenset()
        return frozenset(
            key
            for (key,) in db.query(SnapshotCharacter.character_key)
            .filter(SnapshotCharacter.snapshot_id == snapshot_id)
            .all()
        )

    def load(self, db: Session) -> ArtifactExchangeContext:
        account = self.account(db)
        snapshot_id = account.current_snapshot_id
        quality_config = load_quality_config(db)
        owned = self.owned_character_keys(db, snapshot_id)
        if not snapshot_id:
            return ArtifactExchangeContext(
                snapshot_id=None,
                owned_character_keys=owned,
                quality_config=quality_config,
                characters={},
            )

        targets = latest_targets(db, account.id)
        characters: dict[str, ArtifactCharacterContext] = {}
        for key in owned:
            target_record = targets.get(key)
            artifact_target = (target_record[1].get("artifact") or {}) if target_record else {}
            characters[key] = ArtifactCharacterContext(
                character_key=key,
                artifact_fingerprint=current_artifact_fingerprint(db, account, key),
                target_quality=artifact_target.get("targetQuality", "GOOD"),
                target_version=target_record[0] if target_record else None,
                existing_evaluation=latest_confirmed(db, account.id, key) is not None,
            )
        return ArtifactExchangeContext(
            snapshot_id=snapshot_id,
            owned_character_keys=owned,
            quality_config=quality_config,
            characters=characters,
        )
