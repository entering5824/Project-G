"""Pure Today task-selection and hysteresis policy."""

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class TodaySelectionState:
    pursued_task_id: str | None = None
    pursued_character_key: str | None = None
    pursued_score: float | None = None
    ordering_group: str | None = None
    pursued_config_version: str | None = None
    pinned_character_key: str | None = None


@dataclass(frozen=True)
class TodaySelection:
    primary_task: dict[str, Any] | None
    decision_mode: str
    no_action_reason: str | None
    alternative_tasks: tuple[dict[str, Any], ...]
    pin_status: str | None
    next_state: TodaySelectionState


def ordering_group(task: dict[str, Any]) -> str:
    key = (task.get("primaryGoal") or {}).get("characterKey") or "shared"
    return f"character:{key}"


def strategic_goal_order(global_plan: Iterable[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for goal in global_plan or ():
        key = getattr(goal, "goal_key", None)
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def select_today_task(
    *,
    quick_actions: list[dict[str, Any]],
    farming: list[dict[str, Any]],
    unavailable: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
    state: TodaySelectionState,
    strategic_order: list[str],
    unresolved: Iterable[Any],
    config_version: str,
    reorder_threshold: float,
) -> TodaySelection:
    actionable = [*quick_actions, *farming]
    waiting = [*unavailable, *blocked]
    all_tasks = [*actionable, *waiting]
    pinned = [task for task in actionable if state.pinned_character_key in (task.get("characterKeys") or [])]
    pinned_waiting = [task for task in waiting if state.pinned_character_key in (task.get("characterKeys") or [])]
    ranks = {key: rank for rank, key in enumerate(strategic_order)}
    def goal_order(task):
        key = (task.get("primaryGoal") or {}).get("goalKey")
        return (ranks.get(key, len(ranks)), int(task.get("goalRank", len(ranks))), task["id"])

    if state.pinned_character_key:
        candidate = min(pinned, key=goal_order) if pinned else (min(pinned_waiting, key=goal_order) if pinned_waiting else None)
        decision_mode = "PINNED"
    else:
        candidate = min(actionable, key=goal_order) if actionable else (min(waiting, key=goal_order) if waiting else None)
        decision_mode = "STRATEGIC" if strategic_order else "FALLBACK"
    strategic_character = ((candidate or {}).get("primaryGoal") or {}).get("characterKey")

    pin_status = None
    if state.pinned_character_key:
        if pinned:
            pin_status = "ACTIVE"
        else:
            other = [
                (name, task)
                for name, rows in (("unavailable", unavailable), ("blocked", blocked))
                for task in rows
                if state.pinned_character_key in (task.get("characterKeys") or [])
            ]
            if other:
                pin_status = "UNAVAILABLE" if other[0][0] == "unavailable" else "BLOCKED"
            elif any(
                getattr(issue, "code", None) == "BUILD_PROFILE_MISSING"
                and getattr(issue, "character_key", None) == state.pinned_character_key
                for issue in unresolved
            ):
                pin_status = "MISSING_PROFILE"
            else:
                pin_status = "COMPLETED"

    previous = next((task for task in all_tasks if task["id"] == state.pursued_task_id), None)
    if candidate and previous and not state.pinned_character_key and candidate in actionable:
        same_group = ordering_group(candidate) == state.ordering_group
        same_config = state.pursued_config_version == str(config_version)
        gain = float(candidate.get("score", 0)) - float(previous.get("score", 0))
        if (previous in actionable and same_group and same_config and gain < reorder_threshold
                and previous.get("primaryGoal") == candidate.get("primaryGoal")):
            candidate = previous

    next_state = state
    if candidate:
        next_state = TodaySelectionState(
            pursued_task_id=candidate["id"],
            pursued_character_key=(candidate.get("primaryGoal") or {}).get("characterKey"),
            pursued_score=float(candidate.get("score", 0)),
            ordering_group=ordering_group(candidate),
            pursued_config_version=str(config_version),
            pinned_character_key=state.pinned_character_key,
        )

    if candidate is None:
        no_action_reason = (
            "PINNED_CHARACTER_NO_TASK"
            if state.pinned_character_key
            else "STRATEGIC_CHARACTER_NO_TASK"
            if strategic_character
            else "NO_STRATEGIC_GOAL"
        )
    elif candidate in waiting:
        no_action_reason = (
            "CURRENT_PRIORITY_UNAVAILABLE" if candidate in unavailable else "CURRENT_PRIORITY_BLOCKED"
        )
    else:
        no_action_reason = None

    selected_character = state.pinned_character_key or strategic_character
    alternatives = tuple(
        task
        for task in all_tasks
        if task is not candidate and selected_character not in (task.get("characterKeys") or [])
    )[:3]

    return TodaySelection(
        primary_task=candidate,
        decision_mode=decision_mode,
        no_action_reason=no_action_reason,
        alternative_tasks=alternatives,
        pin_status=pin_status,
        next_state=next_state,
    )
