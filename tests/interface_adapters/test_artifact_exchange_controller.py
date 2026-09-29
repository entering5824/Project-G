from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactExchangeCommit,
    ArtifactExchangePreview,
)
from projectg.interface_adapters.controllers.artifact_exchange_controller import ArtifactExchangeController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request):
        self.request = request
        return self.result


def test_artifact_controller_translates_request_and_response_shapes():
    preview = UseCase(ArtifactExchangePreview("snapshot-1", ({"valid": True},), 1))
    confirm = UseCase(ArtifactExchangeCommit(({"evaluation": "stored"},)))
    controller = ArtifactExchangeController(preview, confirm)

    preview_payload = controller.preview({"rows": []})
    commit_payload = controller.confirm([{"characterKey": "Amber"}], "snapshot-1")

    assert preview.request.payload == {"rows": []}
    assert preview_payload == {"snapshotId": "snapshot-1", "evaluations": [{"valid": True}], "validCount": 1}
    assert confirm.request.preview_snapshot_id == "snapshot-1"
    assert commit_payload == {"evaluations": [{"evaluation": "stored"}]}
