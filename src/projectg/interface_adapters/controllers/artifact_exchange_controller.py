"""Translate artifact exchange inputs and results for desktop presentation."""

from projectg.application.use_cases.artifacts.confirm_exchange import (
    ConfirmArtifactExchange,
    ConfirmArtifactExchangeRequest,
)
from projectg.application.use_cases.artifacts.preview_exchange import (
    PreviewArtifactExchange,
    PreviewArtifactExchangeRequest,
)


class ArtifactExchangeController:
    def __init__(self, preview: PreviewArtifactExchange, confirm: ConfirmArtifactExchange):
        self._preview, self._confirm = preview, confirm

    def preview(self, payload: object) -> dict:
        result = self._preview.execute(PreviewArtifactExchangeRequest(payload))
        return {"snapshotId": result.snapshot_id,
                "evaluations": list(result.evaluations), "validCount": result.valid_count}

    def confirm(self, rows: list[dict], preview_snapshot_id: str) -> dict:
        result = self._confirm.execute(ConfirmArtifactExchangeRequest(tuple(rows), preview_snapshot_id))
        return {"evaluations": list(result.evaluations)}
