from types import SimpleNamespace

from projectg.domain.planning.today.selection import (
    TodaySelectionState,
    select_today_task,
    strategic_goal_order,
)


def _task(task_id: str, character: str, score: float) -> dict:
    return {
        "id": task_id,
        "score": score,
        "primaryGoal": {"characterKey": character, "goalKey": character},
        "characterKeys": [character],
    }


def test_strategic_character_beats_higher_raw_task_score() -> None:
    result = select_today_task(
        quick_actions=[_task("high", "HighTier", 30), _task("low", "LowTier", 99)],
        farming=[],
        unavailable=[],
        blocked=[],
        state=TodaySelectionState(),
        strategic_order=["HighTier", "LowTier"],
        unresolved=[],
        config_version="1",
        reorder_threshold=3.0,
    )
    assert result.primary_task["id"] == "high"
    assert result.decision_mode == "STRATEGIC"


def test_hysteresis_keeps_previous_task_until_threshold_is_met() -> None:
    previous = _task("old", "A", 80)
    candidate = _task("new", "A", 82)
    result = select_today_task(
        quick_actions=[candidate, previous],
        farming=[],
        unavailable=[],
        blocked=[],
        state=TodaySelectionState(
            pursued_task_id="old",
            ordering_group="character:A",
            pursued_config_version="1",
        ),
        strategic_order=["A"],
        unresolved=[],
        config_version="1",
        reorder_threshold=3.0,
    )
    assert result.primary_task["id"] == "old"


def test_pin_can_select_unavailable_task_and_reports_status() -> None:
    closed = _task("closed", "Pinned", 10)
    result = select_today_task(
        quick_actions=[],
        farming=[],
        unavailable=[closed],
        blocked=[],
        state=TodaySelectionState(pinned_character_key="Pinned"),
        strategic_order=["Other"],
        unresolved=[],
        config_version="1",
        reorder_threshold=3.0,
    )
    assert result.primary_task["id"] == "closed"
    assert result.pin_status == "UNAVAILABLE"
    assert result.no_action_reason == "CURRENT_PRIORITY_UNAVAILABLE"


def test_missing_profile_pin_has_explicit_status() -> None:
    issue = SimpleNamespace(code="BUILD_PROFILE_MISSING", character_key="Pinned")
    result = select_today_task(
        quick_actions=[],
        farming=[],
        unavailable=[],
        blocked=[],
        state=TodaySelectionState(pinned_character_key="Pinned"),
        strategic_order=[],
        unresolved=[issue],
        config_version="1",
        reorder_threshold=3.0,
    )
    assert result.pin_status == "MISSING_PROFILE"
    assert result.no_action_reason == "PINNED_CHARACTER_NO_TASK"


def test_strategic_order_deduplicates_characters_without_rescoring() -> None:
    goals = [
        SimpleNamespace(goal_key="A"),
        SimpleNamespace(goal_key="A"),
        SimpleNamespace(goal_key="B"),
    ]
    assert strategic_goal_order(goals) == ["A", "B"]
