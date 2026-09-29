"""Read-only SQLite queries needed by target import and preset workflows."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.target_gateway import TargetImportContext, TargetPresetContext
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import Account, CharacterTargetPreset, SnapshotCharacter
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.repositories.targets import (
    active_preset_keys,
    latest_active_targets,
    latest_target_for_preset,
)


class TargetContextReader:
    """Translate persisted target/account rows into application-facing target facts."""

    def __init__(self, configuration: Settings, game_data_provider: Callable):
        self._configuration = configuration
        self._game_data_provider = game_data_provider

    def account(self, db: Session) -> Account:
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    def import_context(self, db: Session) -> TargetImportContext:
        account = self.account(db)
        latest = latest_active_targets(db, account.id)
        return TargetImportContext(
            available_character_keys=frozenset(self.target_keys(db, account)),
            latest_versions={key: row.version for key, row in latest.items()},
            account_imported=bool(account.current_snapshot_id),
        )

    def preset_context(self, db: Session, character_key: str) -> TargetPresetContext:
        account = self.account(db)
        owned = character_key in self.target_keys(db, account)
        active_key = active_preset_keys(db, account.id).get(character_key, "default")
        current = latest_target_for_preset(db, account.id, character_key, active_key)
        preset_rows = db.scalars(
            select(CharacterTargetPreset).where(
                CharacterTargetPreset.account_id == account.id,
                CharacterTargetPreset.character_key == character_key,
            )
        ).all()
        return TargetPresetContext(
            character_key=character_key,
            owned=owned,
            current_target=deepcopy(current.target_json) if current is not None else None,
            current_preset_key=current.preset_key if current is not None else None,
            existing_preset_keys=frozenset(row.preset_key for row in preset_rows),
        )

    def target_keys(self, db: Session, account: Account) -> set[str]:
        if not account.current_snapshot_id:
            return set()
        keys = set(
            db.scalars(
                select(SnapshotCharacter.character_key).where(
                    SnapshotCharacter.snapshot_id == account.current_snapshot_id
                )
            )
        )
        if any(key.startswith("Traveler") for key in keys):
            catalog_character_keys = set(self._game_data_provider().characters)
            keys.update(key for key in catalog_character_keys if key.startswith("Traveler"))
        return keys
