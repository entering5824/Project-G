from projectg.application.ports.outbound.account_import_gateway import AccountImportPreview
from projectg.domain.game_catalog.models import GameData
from projectg.interface_adapters.controllers.account_import_controller import AccountImportController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request):
        self.request = request
        return self.result


def test_good_file_controller_formats_the_application_result_for_desktop():
    preview = UseCase(AccountImportPreview(
        duplicate=False,
        coverage={"characters": "CURRENT", "weapons": "previous-snapshot"},
        characters=2,
        weapons=3,
        equipped_artifacts=4,
        teams=1,
        warnings=("warning",),
        abnormal_changes=(),
    ))
    controller = AccountImportController(GameData(metadata={}), preview, UseCase(None),
                                         UseCase(None), UseCase(None))

    result = controller.preview_good_file("account.good")

    assert preview.request.key == "account.good"
    assert result["coverage"] == {
        "characters": "included",
        "weapons": "retained stale",
    }
    assert result["equippedArtifacts"] == 4
    assert result["warnings"] == ["warning"]
