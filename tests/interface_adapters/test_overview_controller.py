from projectg.application.ports.outbound.overview_gateway import OverviewData
from projectg.interface_adapters.controllers.overview_controller import OverviewController


class UseCase:
    def execute(self):
        return OverviewData({"snapshotId": "snap-1", "characters": []})


def test_overview_controller_returns_the_desktop_view_payload():
    result = OverviewController(UseCase()).load()

    assert result == {"snapshotId": "snap-1", "characters": []}
