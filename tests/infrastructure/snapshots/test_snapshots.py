import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect

from projectg.application.imports.errors import AbnormalAccountChangeError, DuplicateSnapshotError
from projectg.application.use_cases.imports.commit_account_import import CommitAccountImport, CommitAccountImportRequest
from projectg.application.use_cases.imports.preview_account_import import PreviewAccountImport, PreviewAccountImportRequest
from projectg.bootstrap.settings import settings
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import_gateway import SqliteAccountImportGateway
from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot, SnapshotArtifact, SnapshotCharacter
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.serialization.good_document import GoodDocumentParser
from projectg.infrastructure.serialization.good_importer import GoodImporter


def _imports(db, snapshot_dir, *, id_generator=None):
    configuration = settings.model_copy(update={"snapshot_dir": Path(snapshot_dir)})
    clock = SystemClock()
    ids = id_generator or Uuid4IdGenerator()
    factory = lambda: nullcontext(db)
    gate = DatabaseMaintenanceGate()
    gateway = SqliteAccountImportGateway(
        factory, gate, AccountImportContextReader(configuration),
        AccountImportRawDocumentStorage(configuration.snapshot_dir),
        SqliteMutationUnitOfWork(
            factory, gate, SimpleNamespace(before_mutation=lambda db, reason: None),
            clock, ids),
    )
    parser = GoodDocumentParser(GoodImporter(get_game_data(settings)))
    return PreviewAccountImport(gateway, parser), CommitAccountImport(gateway, parser, clock, ids)


def import_data(commit, db, data, *, allow_regression=False):
    result = commit.execute(CommitAccountImportRequest(
        json.dumps(data).encode(), allow_regression=allow_regression))
    return db.get(Snapshot, result.snapshot_id), (
        db.get(Snapshot, result.previous_snapshot_id) if result.previous_snapshot_id else None)


def test_history_and_duplicate(db_session, tmp_path, good_json):
    _, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id
    changed = json.loads(json.dumps(good_json)); changed["characters"][0]["level"] = 90
    second, previous = import_data(commit, db_session, changed)
    assert previous.id == first.id and second.previous_snapshot_id == first.id
    assert db_session.get(Snapshot, first.id) is not None
    with pytest.raises(DuplicateSnapshotError):
        import_data(commit, db_session, changed)


def test_invalid_import_does_not_replace_current(db_session, tmp_path, good_json):
    _, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    invalid = {"format": "BAD", "characters": []}
    with pytest.raises(Exception):
        import_data(commit, db_session, invalid)
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id
    assert db_session.query(Snapshot).count() == 1


def test_database_failure_rolls_back_pointer_and_raw_file(db_session, tmp_path, good_json, monkeypatch):
    _, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    changed = json.loads(json.dumps(good_json)); changed["characters"][0]["level"] = 90

    def fail_commit():
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError):
        import_data(commit, db_session, changed)
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id
    assert db_session.query(Snapshot).count() == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_good_import_discards_material_inventory_and_retains_unprovided_sections(db_session, tmp_path, good_json):
    _, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    partial = {
        "format": "GOOD",
        "characters": json.loads(json.dumps(good_json["characters"])),
        "materials": {"Mora": 8_430_000},
    }
    partial["characters"][0]["level"] += 1
    second, previous = import_data(commit, db_session, partial)

    assert previous.id == first.id
    assert second.coverage_json["characters"] == second.id
    assert second.coverage_json["artifacts"] == first.id
    assert "materials" not in second.coverage_json
    assert db_session.query(SnapshotCharacter).filter_by(snapshot_id=second.id).count() == 2
    assert db_session.query(SnapshotArtifact).filter_by(snapshot_id=second.id).count() == 2
    assert not ({"inventory_entries", "inventory_reserves", "inventory_state", "snapshot_material_inventory"}
                & set(inspect(db_session.get_bind()).get_table_names()))
    raw_payload = json.loads(Path(second.raw_path).read_text(encoding="utf-8"))
    assert "materials" not in raw_payload


def test_good_conflict_guard_catches_missing_character_and_weapon_regression(db_session, tmp_path, good_json):
    preview, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    changed = json.loads(json.dumps(good_json))
    changed["characters"] = [character for character in changed["characters"]
                              if character["key"] != "Fischl"]
    changed["weapons"][0]["level"] -= 1
    for team in changed.get("teams", []):
        team["members"] = [member for member in team.get("members", []) if member != "Fischl"]
    raw = json.dumps(changed).encode()

    result = preview.execute(PreviewAccountImportRequest(raw))
    assert {change["field"] for change in result.abnormal_changes} >= {"owned character", "weapon level"}
    with pytest.raises(AbnormalAccountChangeError):
        commit.execute(CommitAccountImportRequest(raw))
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id


def test_good_conflict_guard_catches_ascension_and_constellation_regression(db_session, tmp_path, good_json):
    preview, commit = _imports(db_session, tmp_path)
    first, _ = import_data(commit, db_session, good_json)
    changed = json.loads(json.dumps(good_json))
    changed["characters"][0]["ascension"] -= 1
    changed["characters"][0]["constellation"] -= 1
    raw = json.dumps(changed).encode()

    result = preview.execute(PreviewAccountImportRequest(raw))
    assert {change["field"] for change in result.abnormal_changes} >= {"ascension", "constellation"}
    with pytest.raises(AbnormalAccountChangeError):
        commit.execute(CommitAccountImportRequest(raw))
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id
