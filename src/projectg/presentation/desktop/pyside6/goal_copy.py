"""Vietnamese labels for planner facts shown in the desktop UI."""

GOAL_LABELS = {
    "CHARACTER_LEVEL": "Cấp nhân vật",
    "CHARACTER_ASCENSION": "Đột phá nhân vật",
    "TALENT_AUTO": "Đánh thường",
    "TALENT_SKILL": "Kỹ năng nguyên tố",
    "TALENT_BURST": "Kỹ năng nộ",
    "WEAPON_LEVEL": "Cấp vũ khí",
    "ARTIFACT_QUALITY": "Chất lượng thánh di vật",
}


def goal_display_title(goal):
    label = GOAL_LABELS.get(goal.get("type") or goal.get("goalType"))
    if label is None:
        return str(goal.get("title") or goal.get("type") or "mục tiêu")
    current = (goal.get("current") or {}).get("value")
    target = (goal.get("strategicTarget") or {}).get("value")
    if target is None:
        target = (goal.get("target") or {}).get("value")
    return f"{label} {current} → {target}" if current is not None and target is not None else label


def today_display_title(task):
    character = (task.get("character") or {}).get("name") or (task.get("character") or {}).get("key")
    goal = (goal_display_title(task) if task.get("goalType") in GOAL_LABELS
            else task.get("title") or "Hành động đề xuất")
    if character:
        # Planner titles can already include the character name (including
        # legacy English goal titles). Keep the name in one place only.
        prefix = character.casefold()
        remainder = goal[len(character):] if goal.casefold().startswith(prefix) else None
        if remainder is not None and (not remainder or remainder[0] in " ·—:-"):
            goal = remainder.lstrip(" ·—:-")
        if not goal:
            return character
    return f"{character} · {goal}" if character else goal


def today_action_copy(value):
    replacements = (
        ("Farm/obtain ", "Thu thập "),
        ("Obtain ", "Nhận "),
        ("Farm ", "Thu thập tại "),
        ("Progress toward this goal", "Tiếp tục nâng cấp mục tiêu này"),
    )
    parts = []
    for part in (value or "").split("; "):
        parts.append(next((translated + part[len(source):]
                           for source, translated in replacements if part.startswith(source)), part))
    return "; ".join(parts)
