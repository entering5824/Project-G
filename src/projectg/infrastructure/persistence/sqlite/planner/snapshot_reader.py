"""Read snapshot rows and serialize them to planner facts."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from projectg.application.ports.outbound.planner_gateway import (
    PlannerSnapshotFact, PlannerCharacterFact, PlannerWeaponFact, PlannerArtifactFact,
)
from projectg.infrastructure.persistence.sqlite.models import (
    Account, SnapshotCharacter, SnapshotWeapon, SnapshotArtifact,
)
from projectg.infrastructure.persistence.sqlite.artifacts.service import artifact_fingerprint


class PlannerSnapshotReader:
    def __init__(self, db: Session):
        self._db = db

    def read(self, account_id: str) -> PlannerSnapshotFact:
        account = self._db.get(Account, account_id)
        if account is None or not account.current_snapshot_id:
            return PlannerSnapshotFact(None)
        snapshot_id = account.current_snapshot_id
        db = self._db
        character_rows = db.scalars(
            select(SnapshotCharacter)
            .where(SnapshotCharacter.snapshot_id == snapshot_id)
            .order_by(SnapshotCharacter.character_key)
        ).all()
        weapon_ids = {
            row.equipped_weapon_instance_id
            for row in character_rows
            if row.equipped_weapon_instance_id
        }
        weapons = {}
        if weapon_ids:
            weapons = {
                row.weapon_instance_id: row
                for row in db.scalars(
                    select(SnapshotWeapon).where(
                        SnapshotWeapon.snapshot_id == snapshot_id,
                        SnapshotWeapon.weapon_instance_id.in_(weapon_ids),
                    )
                ).all()
            }

        artifact_rows = db.scalars(
            select(SnapshotArtifact)
            .where(SnapshotArtifact.snapshot_id == snapshot_id)
            .order_by(
                SnapshotArtifact.character_key,
                SnapshotArtifact.slot_key,
                SnapshotArtifact.artifact_instance_id,
            )
        ).all()
        artifacts_by_character: dict[str, dict[str, PlannerArtifactFact]] = {}
        fingerprint_rows: dict[str, list[SnapshotArtifact]] = {}
        for item in artifact_rows:
            fingerprint_rows.setdefault(item.character_key, []).append(item)
            artifacts_by_character.setdefault(item.character_key, {})[
                item.slot_key.lower()
            ] = PlannerArtifactFact(
                set_key=item.set_key,
                rv=item.rv,
                rv_status=item.rv_status,
                level=item.level,
                main_stat=item.main_stat_key,
            )
        fingerprints = {
            key: artifact_fingerprint(rows)
            for key, rows in fingerprint_rows.items()
        }

        characters: list[PlannerCharacterFact] = []
        for row in character_rows:
            weapon_row = weapons.get(row.equipped_weapon_instance_id)
            weapon = (
                PlannerWeaponFact(
                    weapon_row.weapon_instance_id,
                    weapon_row.weapon_key,
                    weapon_row.level,
                    weapon_row.ascension,
                )
                if weapon_row else None
            )
            characters.append(PlannerCharacterFact(
                key=row.character_key,
                level=row.level,
                ascension=row.ascension,
                talents={
                    "auto": row.talent_auto,
                    "skill": row.talent_skill,
                    "burst": row.talent_burst,
                },
                constellation=row.constellation,
                weapon=weapon,
                artifact_fingerprint=fingerprints.get(row.character_key),
                artifacts=artifacts_by_character.get(row.character_key, {}),
            ))

        return PlannerSnapshotFact(snapshot_id, tuple(characters))
