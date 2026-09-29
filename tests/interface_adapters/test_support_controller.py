from projectg.application.ports.outbound.support_gateway import LogDirectory, SupportData
from projectg.interface_adapters.controllers.support_controller import SupportController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, *args):
        self.request = args
        return self.result


def test_support_controller_returns_boundary_values():
    history = UseCase(SupportData({"items": [1]}))
    compare = UseCase(SupportData({"changes": [2]}))
    controller = SupportController(history, compare, UseCase(SupportData({})),
                                   UseCase(SupportData({})), UseCase(SupportData({})),
                                   UseCase(LogDirectory("logs")))

    assert controller.history() == {"items": [1]}
    assert controller.compare_history("before", "after") == {"changes": [2]}
    assert compare.request[0].from_snapshot_id == "before"
    assert controller.logs_directory() == "logs"
