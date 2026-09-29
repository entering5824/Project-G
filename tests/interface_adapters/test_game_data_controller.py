from projectg.application.game_data.models import GameDataPackResult
from projectg.interface_adapters.controllers.game_data_controller import GameDataController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request=None):
        self.request = request
        return self.result


def test_install_controller_keeps_optional_backup_path_in_response():
    result = GameDataPackResult("installed.json", {}, {}, {}, backup_path=None)
    status = UseCase(result)
    install = UseCase(result)
    controller = GameDataController(status, UseCase(result), install, UseCase(result))

    payload = controller.install("candidate.json")

    assert install.request.path == "candidate.json"
    assert payload["backupPath"] is None


def test_preview_controller_projects_nested_current_status():
    current = GameDataPackResult("installed.json", {"dataVersion": "old"}, {}, {})
    preview = GameDataPackResult(
        "candidate.json", {"dataVersion": "new"}, {}, {}, current=current
    )
    controller = GameDataController(UseCase(current), UseCase(preview), UseCase(current), UseCase(current))

    payload = controller.preview("candidate.json")

    assert payload["current"]["path"] == "installed.json"
    assert payload["current"]["metadata"]["dataVersion"] == "old"
