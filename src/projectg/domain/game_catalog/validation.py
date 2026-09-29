from collections import Counter
from typing import Any
from projectg.domain.game_catalog.models import GameData


class GameDataValidationError(ValueError):
    def __init__(self, problems: list[dict[str, Any]]):
        self.problems = problems
        super().__init__(f"Invalid GameData: {len(problems)} validation issue(s)")


def validate_game_data(data: GameData) -> None:
    problems: list[dict[str, Any]] = []
    if not all(data.metadata.get(k) for k in ("schema_version", "game_version", "data_version", "generated_at", "source")):
        problems.append({"code": "METADATA_INCOMPLETE"})
    for kind, rows in (("character", data.characters), ("weapon", data.weapons), ("material", data.materials),
                       ("domain", data.domains), ("boss", data.bosses)):
        # Normalization rejects duplicate entity keys before records are built.
        for key in rows:
            if not key or key.strip() != key:
                problems.append({"code": "INVALID_STABLE_KEY", "entity": kind, "key": key})
    families: dict[str, list[int]] = {}
    for item in data.materials.values():
        if (item.family_key is None) != (item.tier is None):
            problems.append({"code": "INVALID_MATERIAL_FAMILY", "materialKey": item.key})
        if item.family_key:
            families.setdefault(item.family_key, []).append(int(item.tier))
        recipe = item.craft_recipe
        if recipe:
            source = data.materials.get(recipe.get("from_material"))
            if not source or source.family_key != item.family_key or source.tier is None or item.tier is None or source.tier >= item.tier:
                problems.append({"code": "INVALID_CRAFT_RECIPE", "materialKey": item.key})
            elif int(recipe.get("consume_amount", 0)) != 3 or int(recipe.get("produce_amount", 0)) != 1:
                problems.append({"code": "INVALID_CRAFT_RECIPE", "materialKey": item.key})
        source = item.source or {}
        boss_key = source.get("bossKey") or source.get("boss_key")
        if boss_key and boss_key not in data.bosses:
            problems.append({"code":"BROKEN_BOSS_SOURCE","materialKey":item.key,"bossKey":boss_key})
    for key, tiers in families.items():
        if sorted(tiers) != list(range(1, max(tiers) + 1)):
            problems.append({"code": "MATERIAL_TIER_GAP", "familyKey": key, "tiers": sorted(tiers)})
    for character in data.characters.values():
        refs = [character.local_specialty, character.normal_boss_material, character.gem_family]
        refs += [character.enemy_material_family, character.talent_book_family, *character.weekly_boss_materials]
        for ref in filter(None, refs):
            if ref not in data.materials and not any(m.family_key == ref for m in data.materials.values()) and ref not in data.bosses:
                problems.append({"code": "BROKEN_REFERENCE", "entity": "character", "key": character.key, "reference": ref})
    for weapon in data.weapons.values():
        for ref in filter(None, (weapon.weapon_ascension_material_family, weapon.enemy_material_family)):
            if ref not in data.materials and not any(m.family_key == ref for m in data.materials.values()):
                problems.append({"code": "BROKEN_REFERENCE", "entity": "weapon", "key": weapon.key, "reference": ref})
    for domain in data.domains.values():
        for ref in domain.reward_material_families:
            if ref not in data.materials and not any(m.family_key == ref for m in data.materials.values()):
                problems.append({"code": "UNKNOWN_DOMAIN_REWARD", "domainKey": domain.key, "materialFamily": ref})
        if domain.schedule_group and domain.schedule_group.upper() not in {"MON_THU","MON_THU_SUN","TUE_FRI","WED_SAT","DAILY"}:
            problems.append({"code":"INVALID_DOMAIN_SCHEDULE","domainKey":domain.key,"scheduleGroup":domain.schedule_group})
    for artifact_set in data.artifact_sets.values():
        if artifact_set.domain_key not in data.domains:
            problems.append({"code":"BROKEN_ARTIFACT_DOMAIN","artifactSetKey":artifact_set.key,"domainKey":artifact_set.domain_key})
    for path, steps in data.steps.items():
        ordered = sorted(steps, key=lambda s: (s.from_value, s.to_value))
        for step in ordered:
            for requirement in step.requirements:
                key = requirement.get("material_key", "")
                if not key.startswith("$CHAR_") and not key.startswith("$WEAPON_") and key not in data.materials:
                    problems.append({"code": "MISSING_MATERIAL_DEFINITION", "path": path, "materialKey": key})
                if int(requirement.get("amount", 0)) < 0:
                    problems.append({"code": "INVALID_COST_AMOUNT", "path": path})
        for left, right in zip(ordered, ordered[1:]):
            if left.to_value != right.from_value:
                problems.append({"code": "COST_PATH_GAP", "path": path, "from": left.to_value, "nextFrom": right.from_value})
        expected = {"character_level": (1, 90), "character_ascension": (0, 6), "talent": (1, 10),
                    "weapon_level_1": (1, 70), "weapon_level_2": (1, 70),
                    "weapon_level_3": (1, 90), "weapon_level_4": (1, 90), "weapon_level_5": (1, 90)}.get(path)
        if expected and (not ordered or (ordered[0].from_value, ordered[-1].to_value) != expected):
            problems.append({"code": "COST_PATH_INCOMPLETE", "path": path, "expected": expected,
                             "actual": (ordered[0].from_value, ordered[-1].to_value) if ordered else None})
    if problems:
        raise GameDataValidationError(problems)
