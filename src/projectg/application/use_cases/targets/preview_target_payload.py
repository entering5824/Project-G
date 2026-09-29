"""Preview a target document already supplied by the caller."""

from dataclasses import dataclass

from projectg.application.ports.outbound.target_document_source import TargetDocumentSource
from projectg.application.ports.outbound.target_gateway import TargetGateway, TargetImportPreview
from projectg.application.targets.errors import TargetOperationError
from projectg.application.targets.import_policy import build_target_import_preview


MAX_TARGET_DOCUMENT_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class PreviewTargetPayloadRequest:
    payload: object


class PreviewTargetPayload:
    def __init__(self, gateway: TargetGateway, document_source: TargetDocumentSource):
        self._gateway = gateway
        self._document_source = document_source

    def execute(self, request: PreviewTargetPayloadRequest) -> TargetImportPreview:
        if self._document_source.encoded_size(request.payload) > MAX_TARGET_DOCUMENT_BYTES:
            raise TargetOperationError("TARGET_FILE_TOO_LARGE", "Target JSON exceeds 10 MiB.", {})
        context = self._gateway.import_context()
        preview, _ = build_target_import_preview(
            request.payload, context.available_character_keys, context.latest_versions
        )
        return TargetImportPreview(request.payload, preview)
