"""Read-only SQLite facts used by account-import workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.account_import_gateway import AccountImportContext
from projectg.domain.account.models import CharacterState, WeaponState
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot, SnapshotCharacter, SnapshotWeapon
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository, SnapshotRepository


class AccountImportContextReader:
    """Translate current SQLite snapshot rows into application-facing import facts."""

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
    def current_snapshot(db: Session, account: Account) -> Snapshot | None:
        return SnapshotRepository().current(db, account)

    def load(self, db: Session) -> AccountImportContext:
        account = self.account(db)
        current = self.current_snapshot(db, account)
        if current is None:
            return AccountImportContext(None, None, {}, None)

        characters = tuple(
            CharacterState(
                key=row.character_key,
                level=row.level,
                ascension=row.ascension,
                constellation=row.constellation,
                talent_auto=row.talent_auto,
                talent_skill=row.talent_skill,
                talent_burst=row.talent_burst,
                equipped_weapon_instance_id=row.equipped_weapon_instance_id,
            )
            for row in db.scalars(
                select(SnapshotCharacter).where(SnapshotCharacter.snapshot_id == current.id)
            ).all()
        )
        weapons = tuple(
            WeaponState(
                instance_id=row.weapon_instance_id,
                key=row.weapon_key,
                level=row.level,
                ascension=row.ascension,
                refinement=row.refinement,
                location=row.location,
            )
            for row in db.scalars(
                select(SnapshotWeapon).where(SnapshotWeapon.snapshot_id == current.id)
            ).all()
        )
        return AccountImportContext(
            current_snapshot_id=current.id,
            current_canonical_hash=current.canonical_state_hash,
            coverage=dict(current.coverage_json or {}),
            effective_document=dict(current.effective_state_json or {}),
            previous_characters=characters,
            previous_weapons=weapons,
        )
