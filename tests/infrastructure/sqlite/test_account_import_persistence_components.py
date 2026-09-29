from datetime import datetime, timezone

from projectg.application.ports.outbound.account_document_parser import PreparedAccountDocument
from projectg.application.ports.outbound.account_import_gateway import AccountImportCommitCommand
from projectg.domain.account.models import (
    ArtifactState,
    CharacterState,
    NormalizedGood,
    TeamState,
    WeaponState,
)
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import.context_reader import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import.history_effects import AccountImportHistoryEffects
from projectg.infrastructure.persistence.sqlite.account_import.snapshot_writer import AccountSnapshotWriter
from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    Snapshot,
    SnapshotArtifact,
    SnapshotCharacter,
    SnapshotTeam,
    SnapshotWeapon,
)


def _document() -> PreparedAccountDocument:
    state = NormalizedGood(
        good_format="GOOD",
        good_version=3,
        good_db_version=1,
        characters=[CharacterState("Fischl", 80, 5, 6, 8, 8, 8, "weapon-1")],
        weapons=[WeaponState("weapon-1", "TheStringless", 90, 6, 5, "Fischl")],
        artifacts=[ArtifactState(
            "artifact-1", "Fischl", "GoldenTroupe", "flower", 5, 20, "hp",
            substats=[{"key": "critRate_", "value": 3.9}],
        )],
        teams=[TeamState("team-1", "Aggravate", ["Fischl"], {"name": "Aggravate"})],
    )
    return PreparedAccountDocument(
        raw_content=b'{"format":"GOOD"}',
        raw_hash="a" * 64,
        canonical_hash="b" * 64,
        effective_document={"format": "GOOD", "characters": []},
        supplied_sections=frozenset({"characters", "weapons", "artifacts", "teams"}),
        state=state,
        importer_version="test-importer",
    )


def test_account_import_context_reader_maps_current_snapshot_facts(db_session):
    account = Account(id="account-import", name="Account", server_region="NA")
    db_session.add(account)
    db_session.flush()
    snapshot = Snapshot(
        id="snapshot-1",
        account_id=account.id,
        imported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        good_format="GOOD",
        good_version=3,
        good_db_version=1,
        raw_file_hash="raw",
        canonical_state_hash="canonical",
        previous_snapshot_id=None,
        importer_version="test",
        raw_path="snapshot.json",
        coverage_json={"characters": "snapshot-1"},
        effective_state_json={"format": "GOOD", "characters": []},
    )
    db_session.add(snapshot)
    db_session.flush()
    account.current_snapshot_id = snapshot.id
    db_session.add_all([
        SnapshotCharacter(
            snapshot_id=snapshot.id,
            character_key="Fischl",
            level=80,
            ascension=5,
            constellation=6,
            talent_auto=8,
            talent_skill=8,
            talent_burst=8,
            equipped_weapon_instance_id="weapon-1",
        ),
        SnapshotWeapon(
            snapshot_id=snapshot.id,
            weapon_instance_id="weapon-1",
            weapon_key="TheStringless",
            level=90,
            ascension=6,
            refinement=5,
            location="Fischl",
        ),
    ])
    db_session.flush()

    context = AccountImportContextReader(Settings(account_id=account.id)).load(db_session)

    assert context.current_snapshot_id == snapshot.id
    assert context.current_canonical_hash == "canonical"
    assert context.coverage == {"characters": "snapshot-1"}
    assert context.previous_characters[0].key == "Fischl"
    assert context.previous_weapons[0].instance_id == "weapon-1"


def test_account_snapshot_writer_persists_normalized_rows_and_moves_pointer(db_session, tmp_path):
    account = Account(id="account-import", name="Account", server_region="NA")
    db_session.add(account)
    db_session.flush()
    command = AccountImportCommitCommand(
        snapshot_id="snapshot-1",
        imported_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        expected_previous_snapshot_id=None,
        coverage={"characters": "snapshot-1"},
        document=_document(),
    )

    row = AccountSnapshotWriter.persist(
        db_session,
        account,
        None,
        command,
        tmp_path / "snapshot.json",
    )

    assert row.id == "snapshot-1"
    assert account.current_snapshot_id == "snapshot-1"
    assert db_session.query(SnapshotCharacter).filter_by(snapshot_id=row.id).count() == 1
    assert db_session.query(SnapshotWeapon).filter_by(snapshot_id=row.id).count() == 1
    assert db_session.query(SnapshotArtifact).filter_by(snapshot_id=row.id).count() == 1
    assert db_session.query(SnapshotTeam).filter_by(snapshot_id=row.id).count() == 1


def test_account_import_raw_storage_is_atomic_and_cleanup_capable(tmp_path):
    storage = AccountImportRawDocumentStorage(tmp_path / "snapshots")
    imported_at = datetime(2026, 1, 2, 3, 4, 5, 6789, tzinfo=timezone.utc)

    path = storage.write(imported_at, "abcdef123456" * 6, b'{"format":"GOOD"}')

    assert path.read_bytes() == b'{"format":"GOOD"}'
    assert not list(path.parent.glob("*.tmp"))
    assert "abcdef123456" in path.name

    storage.delete(path)
    assert not path.exists()


class _Effects:
    def __init__(self):
        self.diffs = []
        self.reconciliations = []

    def persist_snapshot_diff(self, account_id, previous_id, current_id):
        self.diffs.append((account_id, previous_id, current_id))

    def reconcile_completion(self, account, previous_id, current_id, *, reason):
        self.reconciliations.append((account.id, previous_id, current_id, reason))


def test_account_import_history_effects_delegate_diff_and_completion():
    account = Account(id="account-import", name="Account", server_region="NA")
    previous = Snapshot(
        id="snapshot-0",
        account_id=account.id,
        imported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        good_format="GOOD",
        good_version=3,
        good_db_version=1,
        raw_file_hash="raw",
        canonical_state_hash="canonical",
        previous_snapshot_id=None,
        importer_version="test",
        raw_path="snapshot.json",
        coverage_json={},
        effective_state_json={},
    )
    effects = _Effects()

    AccountImportHistoryEffects.record(effects, account, previous, "snapshot-1")

    assert effects.diffs == [(account.id, "snapshot-0", "snapshot-1")]
    assert effects.reconciliations == [
        (account.id, "snapshot-0", "snapshot-1", "ACCOUNT_STATE_CHANGED")
    ]
