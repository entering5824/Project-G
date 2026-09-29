"""Preview an external account document using application-owned import policy."""

from dataclasses import dataclass

from projectg.application.imports.policy import evaluate_account_import
from projectg.application.ports.outbound.account_document_parser import AccountDocumentParser
from projectg.application.ports.outbound.account_import_gateway import AccountImportGateway, AccountImportPreview
from projectg.application.use_cases.imports.import_limits import validate_import_size


@dataclass(frozen=True)
class PreviewAccountImportRequest:
    content: bytes


class PreviewAccountImport:
    def __init__(self, gateway: AccountImportGateway, parser: AccountDocumentParser):
        self._gateway = gateway
        self._parser = parser

    def execute(self, request: PreviewAccountImportRequest) -> AccountImportPreview:
        validate_import_size(request.content)
        context = self._gateway.load_context()
        document = self._parser.prepare(
            request.content,
            previous_effective_document=context.effective_document,
        )
        decision = evaluate_account_import(context, document)
        state = document.state
        return AccountImportPreview(
            duplicate=decision.duplicate,
            coverage=decision.coverage,
            characters=len(state.characters),
            weapons=len(state.weapons),
            equipped_artifacts=len(state.artifacts),
            teams=len(state.teams),
            warnings=tuple(state.warnings),
            abnormal_changes=decision.regressions,
        )
