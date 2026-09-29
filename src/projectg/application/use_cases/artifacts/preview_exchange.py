"""Preview externally supplied artifact evaluation records."""

from dataclasses import dataclass

from projectg.application.artifacts.policy import build_artifact_exchange_preview
from projectg.application.ports.outbound.artifact_document_parser import ArtifactDocumentParser
from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactExchangeGateway,
    ArtifactExchangePreview,
)


@dataclass(frozen=True)
class PreviewArtifactExchangeRequest:
    payload: object


class PreviewArtifactExchange:
    def __init__(self, gateway: ArtifactExchangeGateway, parser: ArtifactDocumentParser):
        self._gateway = gateway
        self._parser = parser

    def execute(self, request: PreviewArtifactExchangeRequest) -> ArtifactExchangePreview:
        parsed = self._parser.parse(request.payload)
        return build_artifact_exchange_preview(parsed, self._gateway.load_context())
