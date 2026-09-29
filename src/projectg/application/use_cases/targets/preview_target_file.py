"""Preview a target document selected from local storage."""

from dataclasses import dataclass

from projectg.application.ports.outbound.target_document_source import TargetDocumentSource
from projectg.application.ports.outbound.target_gateway import TargetGateway, TargetImportPreview
from projectg.application.targets.import_policy import build_target_import_preview


@dataclass(frozen=True)
class PreviewTargetFileRequest:
    path: str


class PreviewTargetFile:
    def __init__(self, gateway: TargetGateway, document_source: TargetDocumentSource):
        self._gateway = gateway
        self._document_source = document_source

    def execute(self, request: PreviewTargetFileRequest) -> TargetImportPreview:
        payload = self._document_source.read(request.path)
        context = self._gateway.import_context()
        preview, _ = build_target_import_preview(
            payload, context.available_character_keys, context.latest_versions
        )
        return TargetImportPreview(payload, preview)
