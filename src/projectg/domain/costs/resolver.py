from collections import defaultdict
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.models import UpgradeGoal, GoalType
from .models import CostStatus, ResolvedCost


def weapon_required_ascension(level: int) -> int:
    """Return the weapon ascension phase required to reach ``level``."""
    if level <= 20:
        return 0
    if level <= 40:
        return 1
    if level <= 50:
        return 2
    if level <= 60:
        return 3
    if level <= 70:
        return 4
    if level <= 80:
        return 5
    return 6


def _add_step_requirements(game: GameData, path, low: int, high: int,
                           requirements: dict[str, int]) -> bool:
    """Merge the overlapping step costs. False means a material template could not be resolved."""
    for step in path:
        if step.from_value >= high or step.to_value <= low:
            continue
        overlap_from, overlap_to = max(low, step.from_value), min(high, step.to_value)
        if overlap_from >= overlap_to:
            continue
        scale = (overlap_to - overlap_from) / (step.to_value - step.from_value)
        for requirement in step.requirements:
            key = requirement["material_key"]
            amount = int(requirement["amount"])
            if key not in game.materials:
                return False
            requirements[key] += int(round(amount * scale))
    return True

def resolve_requirements(game: GameData, goal: UpgradeGoal, target_value: int) -> dict[str, int] | None:
    if goal.type == GoalType.WEAPON_LEVEL:
        if not goal.weapon_key or goal.weapon_key not in game.weapons:
            return None
        weapon = game.weapons[goal.weapon_key]
        if target_value > weapon.max_level:
            return None
        path = game.steps.get(f"weapon_level_{weapon.rarity}", [])
    elif goal.type == GoalType.CHARACTER_LEVEL:
        if goal.character_key not in game.characters:
            return None
        path = game.steps.get("character_level", [])
    elif goal.type == GoalType.CHARACTER_ASCENSION:
        if goal.character_key not in game.characters:
            return None
        path = game.steps.get(f"character_ascension:{goal.character_key}",
                              game.steps.get("character_ascension", []))
    elif goal.type in (GoalType.TALENT_AUTO, GoalType.TALENT_SKILL, GoalType.TALENT_BURST):
        if goal.character_key not in game.characters:
            return None
        # Character-specific paths retain exact talent materials and exceptions.
        path = game.steps.get(f"talent:{goal.character_key}", game.steps.get("talent", []))
    else:
        return None
    requirements: dict[str, int] = defaultdict(int)
    low, high = int(goal.current_value), int(target_value)
    for step in path:
        if step.from_value >= high or step.to_value <= low:
            continue
        overlap_from, overlap_to = max(low, step.from_value), min(high, step.to_value)
        if overlap_from >= overlap_to:
            continue
        scale = (overlap_to - overlap_from) / (step.to_value - step.from_value)
        for requirement in step.requirements:
            key = requirement["material_key"]
            amount = int(requirement["amount"])
            if key.startswith("$CHAR_"):
                definition = game.characters.get(goal.character_key)
                token = key.removeprefix("$CHAR_")
                if token == "SPECIALTY":
                    token = "LOCAL_SPECIALTY"
                resolved_key = definition.material_keys.get(token) if definition else None
                if token.endswith(("_T1", "_T2", "_T3", "_T4")):
                    family_label, tier = token.rsplit("_T", 1)
                    family = definition.material_keys.get(family_label) if definition else None
                    candidates = [m for m in game.materials.values() if m.family_key == family and m.tier == int(tier)]
                    resolved_key = candidates[0].key if candidates else None
                if not resolved_key:
                    return None
                key = resolved_key
            elif key.startswith("$WEAPON_"):
                # This milestone's weapon level path does not currently need weapon-specific templates.
                return None
            if key not in game.materials:
                return None
            requirements[key] += int(round(amount * scale))

    if goal.type == GoalType.WEAPON_LEVEL and goal.weapon_key:
        ascension_path = game.steps.get(f"weapon_ascension:{goal.weapon_key}")
        if ascension_path:
            current_phase = int(goal.weapon_ascension or 0)
            target_phase = weapon_required_ascension(high)
            if target_phase > current_phase and not _add_step_requirements(
                    game, ascension_path, current_phase, target_phase, requirements):
                return None
    return dict(requirements)


def resolve_cost(game: GameData, requirements: dict[str, int] | None) -> ResolvedCost:
    """Return a theoretical cost estimate, never an ownership or availability claim."""
    if requirements is None:
        return ResolvedCost({}, CostStatus.COST_DATA_MISSING, flags=["GAME_DATA_MISSING"])
    required = dict(sorted(requirements.items()))
    sources = {key: game.materials[key].source or {} for key in required}
    info = {key: {"name": game.materials[key].name, "category": game.materials[key].category,
                  "familyKey": game.materials[key].family_key, "tier": game.materials[key].tier}
            for key in required}
    return ResolvedCost(required, CostStatus.ESTIMATED, sources=sources, material_info=info)
