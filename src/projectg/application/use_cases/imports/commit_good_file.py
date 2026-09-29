"""Read a selected GOOD file and commit its account import."""

from dataclasses import dataclass

from projectg.application.ports.outbound.account_import_gateway import AccountImportCommit
from projectg.application.ports.outbound.file_storage import FileStorage
from projectg.application.use_cases.imports.commit_account_import import (
    CommitAccountImport,
    CommitAccountImportRequest,
)


@dataclass(frozen=True)
class CommitGoodFileRequest:
    key: str
    allow_regression: bool = False


class CommitGoodFile:
    def __init__(self, storage: FileStorage, use_case: CommitAccountImport):
        self._storage, self._use_case = storage, use_case

    def execute(self, request: CommitGoodFileRequest) -> AccountImportCommit:
        return self._use_case.execute(CommitAccountImportRequest(
            self._storage.read(request.key), request.allow_regression))
