"""Commit an external account document after application-owned validation."""

from dataclasses import dataclass

from projectg.application.imports.errors import AbnormalAccountChangeError, DuplicateSnapshotError
from projectg.application.imports.policy import evaluate_account_import
from projectg.application.ports.outbound.account_document_parser import AccountDocumentParser
from projectg.application.ports.outbound.account_import_gateway import (
    AccountImportCommit,
    AccountImportCommitCommand,
    AccountImportGateway,
)
from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.application.use_cases.imports.import_limits import validate_import_size


@dataclass(frozen=True)
class CommitAccountImportRequest:
    content: bytes
    allow_regression: bool = False


class CommitAccountImport:
    def __init__(self, gateway: AccountImportGateway, parser: AccountDocumentParser,
                 clock: Clock, id_generator: IdGenerator):
        self._gateway = gateway
        self._parser = parser
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: CommitAccountImportRequest) -> AccountImportCommit:
        validate_import_size(request.content)
        context = self._gateway.load_context()
        document = self._parser.prepare(
            request.content,
            previous_effective_document=context.effective_document,
        )
        decision = evaluate_account_import(context, document)
        if decision.duplicate:
            raise DuplicateSnapshotError
        if decision.regressions and not request.allow_regression:
            raise AbnormalAccountChangeError(list(decision.regressions))
        snapshot_id = self._id_generator.next_id()
        coverage = {
            section: (snapshot_id if source == "CURRENT" else source)
            for section, source in decision.coverage.items()
        }
        return self._gateway.commit_validated(AccountImportCommitCommand(
            snapshot_id=snapshot_id,
            imported_at=self._clock.now(),
            expected_previous_snapshot_id=context.current_snapshot_id,
            coverage=coverage,
            document=document,
        ))
