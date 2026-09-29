from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.domain.account.models import (
    ArtifactState,
    CharacterState,
    NormalizedGood,
    TeamState,
    WeaponState,
)
from projectg.domain.history.diff import compare_account_snapshots
from projectg.infrastructure.persistence.sqlite.history.events import record_event
from projectg.infrastructure.persistence.sqlite.models import (
    Snapshot,
    SnapshotArtifact,
    SnapshotCharacter,
    SnapshotTeam,
    SnapshotWeapon,
)


def _snapshot_state(db: Session, snapshot_id: str) -> NormalizedGood:
    characters = [
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
            select(SnapshotCharacter)
            .where(SnapshotCharacter.snapshot_id == snapshot_id)
            .order_by(SnapshotCharacter.character_key)
        ).all()
    ]
    weapons = [
        WeaponState(
            instance_id=row.weapon_instance_id,
            key=row.weapon_key,
            level=row.level,
            ascension=row.ascension,
            refinement=row.refinement,
            location=row.location,
        )
        for row in db.scalars(
            select(SnapshotWeapon)
            .where(SnapshotWeapon.snapshot_id == snapshot_id)
            .order_by(SnapshotWeapon.weapon_instance_id)
        ).all()
    ]
    artifacts = [
        ArtifactState(
            instance_id=row.artifact_instance_id,
            character_key=row.character_key,
            set_key=row.set_key,
            slot_key=row.slot_key,
            rarity=row.rarity,
            level=row.level,
            main_stat_key=row.main_stat_key,
            substats=row.substats_json or [],
            unactivated_substats=row.unactivated_substats_json or [],
            rv=row.rv,
            rv_status=row.rv_status,
            rv_formula_version=row.rv_formula_version,
        )
        for row in db.scalars(
            select(SnapshotArtifact)
            .where(SnapshotArtifact.snapshot_id == snapshot_id)
            .order_by(
                SnapshotArtifact.character_key,
                SnapshotArtifact.slot_key,
                SnapshotArtifact.artifact_instance_id,
            )
        ).all()
    ]
    teams = [
        TeamState(
            team_id=row.team_id,
            name=row.name,
            members=row.members_json or [],
            raw_config=row.raw_config_json,
        )
        for row in db.scalars(
            select(SnapshotTeam)
            .where(SnapshotTeam.snapshot_id == snapshot_id)
            .order_by(SnapshotTeam.team_id)
        ).all()
    ]
    return NormalizedGood("GOOD", None, None, characters, weapons, artifacts, teams)


def compare_snapshots(db: Session, from_id: str | None, to_id: str) -> dict:
    before_row = db.get(Snapshot, from_id) if from_id else None
    after_row = db.get(Snapshot, to_id)
    if after_row is None or (from_id and before_row is None):
        raise LookupError("Snapshot not found.")
    if before_row and before_row.account_id != after_row.account_id:
        raise LookupError("Snapshots belong to different accounts.")

    before = _snapshot_state(db, from_id) if from_id else None
    after = _snapshot_state(db, to_id)
    return compare_account_snapshots(
        before,
        after,
        from_snapshot_id=from_id,
        to_snapshot_id=to_id,
    )


def persist_snapshot_diff(
    db: Session,
    account_id: str,
    from_id: str | None,
    to_id: str,
    *,
    clock: Clock,
    id_generator: IdGenerator,
):
    diff = compare_snapshots(db, from_id, to_id)
    snapshot = db.get(Snapshot, to_id)
    for item in diff["changes"]:
        record_event(
            db,
            account_id,
            "SNAPSHOT",
            item["eventType"],
            item["payload"],
            snapshot_id=to_id,
            character_key=item["characterKey"],
            created_at=snapshot.imported_at if snapshot else None,
            clock=clock,
            id_generator=id_generator,
        )
    return diff


def snapshot_index(db: Session, account_id: str, snapshot_id: str) -> int:
    ids = db.scalars(
        select(Snapshot.id)
        .where(Snapshot.account_id == account_id)
        .order_by(Snapshot.imported_at, Snapshot.id)
    ).all()
    try:
        return ids.index(snapshot_id) + 1
    except ValueError:
        return 0
