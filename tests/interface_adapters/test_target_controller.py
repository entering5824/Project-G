from projectg.application.ports.outbound.target_gateway import TargetImportPreview, TargetOperationResult
from projectg.interface_adapters.controllers.target_controller import TargetController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request):
        self.request = request
        return self.result


def test_target_controller_translates_preview_and_commit_payloads():
    preview_file = UseCase(TargetImportPreview({"targets": {}}, {"canImport": True}))
    commit = UseCase(TargetOperationResult({"saved": ["Amber"]}))
    controller = TargetController(preview_file, UseCase(None), commit, UseCase(None), UseCase(None))

    preview = controller.preview_file("targets.json")
    saved = controller.commit({"targets": {}}, {"Amber"}, "operation-key-123456")

    assert preview_file.request.path == "targets.json"
    assert preview["preview"]["canImport"] is True
    assert saved == {"saved": ["Amber"]}
