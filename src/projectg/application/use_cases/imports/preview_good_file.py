"""Read a selected GOOD file and preview its account import."""

from dataclasses import dataclass

from projectg.application.ports.outbound.account_import_gateway import AccountImportPreview
from projectg.application.ports.outbound.file_storage import FileStorage
from projectg.application.use_cases.imports.preview_account_import import (
    PreviewAccountImport,
    PreviewAccountImportRequest,
)


@dataclass(frozen=True)
class PreviewGoodFileRequest:
    key: str


class PreviewGoodFile:
    def __init__(self, storage: FileStorage, use_case: PreviewAccountImport):
        self._storage, self._use_case = storage, use_case

    def execute(self, request: PreviewGoodFileRequest) -> AccountImportPreview:
        return self._use_case.execute(PreviewAccountImportRequest(self._storage.read(request.key)))
