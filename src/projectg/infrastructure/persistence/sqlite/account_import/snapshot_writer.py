"""SQLite persistence primitive for an already-validated account snapshot."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.account_import_gateway import AccountImportCommitCommand
from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    Snapshot,
    SnapshotArtifact,
    SnapshotCharacter,
    SnapshotTeam,
    SnapshotWeapon,
)


class AccountSnapshotWriter:
    """Persist one immutable normalized snapshot and move the account pointer to it."""

    @staticmethod
    def persist(
        db: Session,
        account: Account,
        previous: Snapshot | None,
        command: AccountImportCommitCommand,
        raw_path: Path,
    ) -> Snapshot:
        document = command.document
        state = document.state
        db.add(account)
        db.flush()
        snapshot = Snapshot(
            id=command.snapshot_id,
            account_id=account.id,
            imported_at=command.imported_at,
            good_format=state.good_format,
            good_version=state.good_version,
            good_db_version=state.good_db_version,
            raw_file_hash=document.raw_hash,
            canonical_state_hash=document.canonical_hash,
            previous_snapshot_id=previous.id if previous else None,
            importer_version=document.importer_version,
            raw_path=str(raw_path),
            coverage_json=command.coverage,
            effective_state_json=document.effective_document,
        )
        db.add(snapshot)

        for value in state.characters:
            db.add(SnapshotCharacter(
                snapshot_id=command.snapshot_id,
                character_key=value.key,
                level=value.level,
                ascension=value.ascension,
                constellation=value.constellation,
                talent_auto=value.talent_auto,
                talent_skill=value.talent_skill,
                talent_burst=value.talent_burst,
                equipped_weapon_instance_id=value.equipped_weapon_instance_id,
            ))
        for value in state.weapons:
            db.add(SnapshotWeapon(
                snapshot_id=command.snapshot_id,
                weapon_instance_id=value.instance_id,
                weapon_key=value.key,
                level=value.level,
                ascension=value.ascension,
                refinement=value.refinement,
                location=value.location,
            ))
        for value in state.artifacts:
            db.add(SnapshotArtifact(
                snapshot_id=command.snapshot_id,
                artifact_instance_id=value.instance_id,
                character_key=value.character_key,
                set_key=value.set_key,
                slot_key=value.slot_key,
                rarity=value.rarity,
                level=value.level,
                main_stat_key=value.main_stat_key,
                substats_json=value.substats,
                unactivated_substats_json=value.unactivated_substats,
                rv=value.rv,
                rv_status=value.rv_status,
                rv_formula_version=value.rv_formula_version,
            ))
        for value in state.teams:
            db.add(SnapshotTeam(
                snapshot_id=command.snapshot_id,
                team_id=value.team_id,
                name=value.name,
                members_json=value.members,
                raw_config_json=value.raw_config,
            ))
        db.flush()
        account.current_snapshot_id = command.snapshot_id
        db.flush()
        return snapshot
