"""SQLite adapter exposing only account catalog keys needed by GameData coverage."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.game_data_account_gateway import AccountCatalogFacts
from projectg.infrastructure.persistence.sqlite.models import Account, SnapshotCharacter, SnapshotWeapon
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class SqliteGameDataAccountGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        account_id: str,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._account_id = account_id

    def load_catalog_facts(self) -> AccountCatalogFacts:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = db.get(Account, self._account_id)
                if account is None or not account.current_snapshot_id:
                    return AccountCatalogFacts()

                characters = list(db.scalars(
                    select(SnapshotCharacter).where(
                        SnapshotCharacter.snapshot_id == account.current_snapshot_id
                    )
                ).all())
                weapon_ids = {
                    row.equipped_weapon_instance_id
                    for row in characters
                    if row.equipped_weapon_instance_id
                }
                weapons = list(db.scalars(
                    select(SnapshotWeapon).where(
                        SnapshotWeapon.snapshot_id == account.current_snapshot_id,
                        SnapshotWeapon.weapon_instance_id.in_(weapon_ids),
                    )
                ).all()) if weapon_ids else []

                return AccountCatalogFacts(
                    character_keys=tuple(row.character_key for row in characters),
                    equipped_weapon_keys=tuple(row.weapon_key for row in weapons),
                )
