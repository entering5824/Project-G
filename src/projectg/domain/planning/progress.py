from bisect import bisect_left
from .config import PlannerConfig


def milestone_position(value: int, milestones: tuple[int, ...]) -> float:
    """Piecewise progress along upgrade milestones, with linear interpolation."""
    if not milestones:
        return 0.0
    if value <= milestones[0]:
        return 0.0
    if value >= milestones[-1]:
        return float(len(milestones) - 1)
    upper_index = bisect_left(milestones, value)
    lower = milestones[upper_index - 1]
    upper = milestones[upper_index]
    return upper_index - 1 + (value - lower) / (upper - lower)


def milestone_deficiency(current: int, target: int, milestones: tuple[int, ...]) -> float:
    if current >= target:
        return 0.0
    target_position = milestone_position(target, milestones)
    current_position = milestone_position(current, milestones)
    return clamp((target_position - current_position) / max(target_position, 1.0))


def character_level_deficiency(current: int, target: int, config: PlannerConfig) -> float:
    return milestone_deficiency(current, target, config.level_milestones)


def weapon_level_deficiency(current: int, target: int, config: PlannerConfig) -> float:
    return milestone_deficiency(current, target, config.weapon_milestones)


def ascension_deficiency(current: int, target: int) -> float:
    if current >= target:
        return 0.0
    return clamp((target - current) / max(target, 1))


def talent_deficiency(current: int, target: int) -> float:
    if current >= target:
        return 0.0
    return clamp((target - current) / max(target - 1, 1))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def next_milestone(current: int, target: int, milestones: tuple[int, ...], cap: int | None = None) -> int:
    maximum = min(target, cap) if cap is not None else target
    for milestone in milestones:
        if milestone > current and milestone <= maximum:
            return milestone
    return maximum if current < maximum else current


def required_ascension_for_talent(target: int, config: PlannerConfig) -> int:
    required = 0
    for minimum_rank, ascension in config.talent_ascension_requirements:
        if target >= minimum_rank:
            required = ascension
    return required
