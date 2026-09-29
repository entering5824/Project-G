import pytest

from projectg.application.ports.outbound.planner_state_gateway import PinContext, PinState
from projectg.application.use_cases.planner_state.preview_pin import PreviewPin, PreviewPinRequest
from projectg.application.use_cases.planner_state.set_pin import SetPin, SetPinRequest


class FakeGateway:
    def __init__(self, *, owned=True):
        self.owned = owned
        self.preview_key = None
        self.pin_key = "unchanged"

    def list_runs(self, limit):
        raise AssertionError("not used")

    def replay_run(self, run_id):
        raise AssertionError("not used")

    def load_pin_context(self, character_key):
        self.preview_key = character_key
        return PinContext(
            owned=self.owned,
            today_plan={
                "primaryTask": {"id": "strategic", "score": 5, "characterKeys": ["Other"]},
                "quickActions": [
                    {"id": "amber-low", "score": 10, "characterKeys": ["Amber"]},
                    {"id": "amber-high", "score": 20, "characterKeys": ["Amber"]},
                ],
                "farming": [],
            },
        )

    def owns_character(self, character_key):
        return self.owned

    def persist_pin(self, character_key):
        self.pin_key = character_key
        return PinState(character_key)


def test_pin_use_cases_own_preview_policy_and_persistence_validation():
    gateway = FakeGateway()

    preview = PreviewPin(gateway).execute(PreviewPinRequest("Amber"))
    state = SetPin(gateway).execute(SetPinRequest(None))

    assert gateway.preview_key == "Amber"
    assert preview.status == "READY"
    assert preview.candidate["id"] == "amber-high"
    assert preview.strategic_task["id"] == "strategic"
    assert gateway.pin_key is None
    assert state.pinned_character_key is None


def test_pin_use_cases_reject_unowned_character_before_persisting():
    gateway = FakeGateway(owned=False)

    with pytest.raises(ValueError, match="not owned"):
        PreviewPin(gateway).execute(PreviewPinRequest("Amber"))
    with pytest.raises(ValueError, match="not owned"):
        SetPin(gateway).execute(SetPinRequest("Amber"))

    assert gateway.pin_key == "unchanged"


def test_pin_preview_uses_farming_candidate_when_no_quick_action_exists():
    class FarmingGateway(FakeGateway):
        def load_pin_context(self, character_key):
            return PinContext(
                owned=True,
                today_plan={
                    "primaryTask": None,
                    "quickActions": [],
                    "farming": [{"id": "farm", "score": 7, "characterKeys": [character_key]}],
                },
            )

    preview = PreviewPin(FarmingGateway()).execute(PreviewPinRequest("Amber"))
    assert preview.status == "READY"
    assert preview.candidate["id"] == "farm"
