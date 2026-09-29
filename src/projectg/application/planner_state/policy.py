"""Application policy for previewing a Today character pin."""

from projectg.application.ports.outbound.planner_state_gateway import PinContext, PinPreview


def build_pin_preview(character_key: str, context: PinContext) -> PinPreview:
    if not context.owned:
        raise ValueError("Character is not owned in the current snapshot.")

    plan = context.today_plan
    current = plan.get("primaryTask")
    candidates = [
        task
        for section in ("quickActions", "farming")
        for task in plan.get(section, [])
        if character_key in (task.get("characterKeys") or [])
    ]
    candidate = (
        max(candidates, key=lambda task: float(task.get("score", 0)))
        if candidates else None
    )
    return PinPreview(
        character_key=character_key,
        candidate=candidate,
        strategic_task=current,
        conflicts=(),
        requires_confirmation=False,
        status="READY" if candidate else "NO_TASK",
    )
