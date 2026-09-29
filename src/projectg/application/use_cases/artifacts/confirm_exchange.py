"""Confirm selected artifact evaluation records against a preview."""

from dataclasses import dataclass
from typing import Any

from projectg.application.artifacts.policy import prepare_artifact_exchange_commit
from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactExchangeCommit,
    ArtifactExchangeCommitCommand,
    ArtifactExchangeGateway,
)


@dataclass(frozen=True)
class ConfirmArtifactExchangeRequest:
    rows: tuple[dict[str, Any], ...]
    preview_snapshot_id: str


class ConfirmArtifactExchange:
    def __init__(self, gateway: ArtifactExchangeGateway):
        self._gateway = gateway

    def execute(self, request: ConfirmArtifactExchangeRequest) -> ArtifactExchangeCommit:
        context = self._gateway.load_context()
        decisions = prepare_artifact_exchange_commit(
            request.rows,
            request.preview_snapshot_id,
            context,
        )
        return self._gateway.commit_validated(ArtifactExchangeCommitCommand(
            expected_snapshot_id=request.preview_snapshot_id,
            evaluations=decisions,
        ))
