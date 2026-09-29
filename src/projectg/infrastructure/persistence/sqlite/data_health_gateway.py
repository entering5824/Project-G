"""SQLite adapter that exposes only persisted facts needed by Data Health."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.data_health_gateway import DataHealthFacts
from projectg.infrastructure.persistence.sqlite.artifacts.service import load_quality_config
from projectg.infrastructure.persistence.sqlite.models import Account, SnapshotCharacter, SnapshotWeapon
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class SqliteDataHealthFactsGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        account_id: str,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._account_id = account_id

    def load_facts(self) -> DataHealthFacts:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                quality_configured = load_quality_config(db).configured
                account = db.get(Account, self._account_id)
                if account is None:
                    return DataHealthFacts(
                        account_available=False,
                        artifact_quality_configured=quality_configured,
                    )
                if not account.current_snapshot_id:
                    return DataHealthFacts(
                        account_available=True,
                        artifact_quality_configured=quality_configured,
                    )

                characters = tuple(
                    db.scalars(
                        select(SnapshotCharacter)
                        .where(SnapshotCharacter.snapshot_id == account.current_snapshot_id)
                        .order_by(SnapshotCharacter.character_key)
                    ).all()
                )
                weapon_ids = {
                    row.equipped_weapon_instance_id
                    for row in characters
                    if row.equipped_weapon_instance_id
                }
                weapons = (
                    tuple(
                        db.scalars(
                            select(SnapshotWeapon).where(
                                SnapshotWeapon.snapshot_id == account.current_snapshot_id,
                                SnapshotWeapon.weapon_instance_id.in_(weapon_ids),
                            )
                        ).all()
                    )
                    if weapon_ids
                    else ()
                )
                return DataHealthFacts(
                    account_available=True,
                    artifact_quality_configured=quality_configured,
                    character_keys=tuple(row.character_key for row in characters),
                    equipped_weapon_keys=tuple(sorted({row.weapon_key for row in weapons})),
                )
