from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
import copy
from types import SimpleNamespace
from contextlib import nullcontext
import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from projectg.infrastructure.persistence.sqlite.support_gateway import SqliteSupportGateway
from projectg.application.use_cases.support.get_history import GetHistory
from projectg.application.use_cases.support.compare_history import CompareHistory, CompareHistoryRequest
from projectg.bootstrap.settings import settings
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.application.use_cases.imports.commit_account_import import CommitAccountImport, CommitAccountImportRequest
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import_gateway import SqliteAccountImportGateway
from projectg.infrastructure.persistence.sqlite.models import Snapshot
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.serialization.good_importer import GoodImporter
from projectg.infrastructure.serialization.good_document import GoodDocumentParser


def _account(db):
    return AccountRepository().get_or_create(
        db, settings.account_id, settings.account_name, settings.server_region
    )


def _commit_good(db_session, snapshot_dir, value):
    configuration = settings.model_copy(update={"snapshot_dir": Path(snapshot_dir)})
    clock = SystemClock()
    ids = Uuid4IdGenerator()
    factory = lambda: nullcontext(db_session)
    gate = DatabaseMaintenanceGate()
    gateway = SqliteAccountImportGateway(
        factory, gate, AccountImportContextReader(configuration),
        AccountImportRawDocumentStorage(configuration.snapshot_dir),
        SqliteMutationUnitOfWork(
            factory, gate, SimpleNamespace(before_mutation=lambda db, reason: None),
            clock, ids),
    )
    parser = GoodDocumentParser(GoodImporter(get_game_data(settings)))
    result = CommitAccountImport(gateway, parser, clock, ids).execute(
        CommitAccountImportRequest(json.dumps(value).encode()))
    snapshot = db_session.get(Snapshot, result.snapshot_id)
    previous = db_session.get(Snapshot, result.previous_snapshot_id) if result.previous_snapshot_id else None
    return snapshot, previous


def test_native_history_compare_and_snapshot_detail_do_not_need_http(
    db_session, good_json, tmp_path
):
    account = _account(db_session)
    first, _ = _commit_good(db_session, tmp_path / "snapshots", good_json)

    newer = copy.deepcopy(good_json)
    raiden = next(row for row in newer["characters"] if row["key"] == "RaidenShogun")
    raiden["level"] = 90
    raiden["talent"]["skill"] = 10
    second, _ = _commit_good(db_session, tmp_path / "snapshots", newer)

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    gateway = SqliteSupportGateway(
        factory, DatabaseMaintenanceGate(), settings
    )

    history = GetHistory(gateway).execute().values
    assert history["currentSnapshotId"] == second.id
    assert [row["id"] for row in history["snapshots"][:2]] == [second.id, first.id]

    compared = CompareHistory(gateway).execute(CompareHistoryRequest(first.id, second.id)).values
    kinds = {row["eventType"] for row in compared["changes"]}
    assert "CHARACTER_LEVEL_CHANGED" in kinds
    assert "TALENT_SKILL_CHANGED" in kinds


def test_native_history_rejects_snapshot_from_another_account(
    db_session, good_json, tmp_path
):
    account = _account(db_session)
    first, _ = _commit_good(db_session, tmp_path / "snapshots", good_json)
    from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot

    db_session.add(Account(id="other-account", name="Other", server_region="ASIA"))
    db_session.add(
        Snapshot(
            id="other-snapshot",
            account_id="other-account",
            good_format="GOOD",
            good_version=1,
            good_db_version=60,
            raw_file_hash="other-raw",
            canonical_state_hash="other-state",
            importer_version="1",
            raw_path="other.json",
        )
    )
    db_session.commit()

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    gateway = SqliteSupportGateway(
        factory, DatabaseMaintenanceGate(), settings
    )

    try:
        CompareHistory(gateway).execute(CompareHistoryRequest(first.id, "other-snapshot"))
    except LookupError:
        pass
    else:
        raise AssertionError("Cross-account snapshot comparison must be rejected")


def test_source_tree_has_no_legacy_web_runtime():
    root = Path(__file__).resolve().parents[2]
    assert (root / "src" / "projectg").is_dir()
    assert not (root / "package.json").exists()
    assert not (root / "vite.config.ts").exists()
    assert not (root / "backend" / "app" / "api").exists()
    assert not (root / "backend" / "app" / "main.py").exists()
    assert not (root / "backend" / "app" / "backend.py").exists()

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8").lower()
    for dependency in ("fastapi", "uvicorn", "python-multipart", "httpx", "hypothesis"):
        assert dependency not in pyproject

    startup = (root / "scripts" / "start-planner.ps1").read_text(encoding="utf-8").lower()
    assert "localhost" not in startup
    assert "uvicorn" not in startup
    assert "-m projectg.main" in startup
