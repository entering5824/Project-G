from projectg.application.ports.outbound.planner_state_gateway import PinPreview, PinState, PlanRunSummary
from projectg.interface_adapters.controllers.planner_state_controller import PlannerStateController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request):
        self.request = request
        return self.result


def test_planner_state_controller_preserves_desktop_result_keys():
    runs = UseCase((PlanRunSummary("run-1", "now", "TODAY", "snap-1", 1, None),))
    replay = UseCase(None)
    preview = UseCase(PinPreview("Amber", None, {"id": "task-1"}, (), False, "READY"))
    pin = UseCase(PinState("Amber"))
    controller = PlannerStateController(runs, replay, preview, pin)

    listed = controller.list_runs(10)
    proposed = controller.preview_pin("Amber")
    changed = controller.set_pin("Amber")

    assert listed[0]["createdAt"] == "now"
    assert proposed["strategicTask"] == {"id": "task-1"}
    assert changed == {"pinnedCharacterKey": "Amber"}
