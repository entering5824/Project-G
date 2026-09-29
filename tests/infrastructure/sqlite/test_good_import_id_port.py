import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from projectg.application.use_cases.imports.commit_account_import import CommitAccountImport, CommitAccountImportRequest
from projectg.bootstrap.settings import settings
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import_gateway import SqliteAccountImportGateway
from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.serialization.good_document import GoodDocumentParser
from projectg.infrastructure.serialization.good_importer import GoodImporter


class FixedIdGenerator:
    def __init__(self):
        self._count = 0

    def next_id(self) -> str:
        self._count += 1
        return "snapshot-from-port" if self._count == 1 else f"event-{self._count}"


def test_good_import_uses_the_injected_id_generator(db_session, good_json, tmp_path):
    ids = FixedIdGenerator()
    clock = SystemClock()
    configuration = settings.model_copy(update={"snapshot_dir": Path(tmp_path / "snapshots")})
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
    commit = CommitAccountImport(gateway, parser, clock, ids)

    result = commit.execute(CommitAccountImportRequest(json.dumps(good_json).encode()))

    assert result.snapshot_id == "snapshot-from-port"
    assert db_session.get(Snapshot, "snapshot-from-port") is not None
    assert db_session.get(Account, settings.account_id).current_snapshot_id == "snapshot-from-port"
