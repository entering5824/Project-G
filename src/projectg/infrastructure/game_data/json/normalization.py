from typing import Any
from projectg.domain.game_catalog.models import (
    GameData, CharacterDefinition, WeaponDefinition, Material, DomainDefinition,
    BossDefinition, ArtifactSetDefinition, UpgradeStepCost,
)


def normalize_game_data(raw: dict[str, Any]) -> GameData:
    """Normalize the stable-key JSON interchange format into immutable records."""
    return GameData(
        metadata=dict(raw.get("metadata") or {}),
        characters={r["key"]: CharacterDefinition(
            key=r["key"], rarity=int(r["rarity"]), element=r["element"], weapon_type=r["weapon_type"],
            region=r["region"], local_specialty=r["local_specialty"],
            normal_boss_material=r["normal_boss_material"], enemy_material_family=r["enemy_material_family"],
            talent_book_family=r["talent_book_family"], weekly_boss_materials=tuple(r.get("weekly_boss_materials", [])),
            gem_family=r.get("gem_family"), material_keys=dict(r.get("material_keys", {})),
            name=r.get("name")) for r in raw.get("characters", [])},
        weapons={r["key"]: WeaponDefinition(r["key"], r["name"], int(r["rarity"]), r["weapon_type"],
            r["weapon_ascension_material_family"], r["enemy_material_family"], r.get("max_level", 90))
            for r in raw.get("weapons", [])},
        materials={r["key"]: Material(r["key"], r["name"], r["category"], r.get("rarity"), r.get("family_key"),
            r.get("tier"), r.get("craft_recipe"), r.get("farmable", True), r.get("source"), r.get("exp_value"))
            for r in raw.get("materials", [])},
        domains={r["key"]: DomainDefinition(r["key"], r["type"], tuple(r["reward_material_families"]),
            r.get("schedule_group"), r.get("name"), int(r.get("resin_cost", 20)))
            for r in raw.get("domains", [])},
        bosses={r["key"]: BossDefinition(r["key"], tuple(r["reward_materials"]), int(r["resin_cost"]), bool(r["weekly_limited"]), r.get("name"))
            for r in raw.get("bosses", [])},
        artifact_sets={r["key"]: ArtifactSetDefinition(r["key"], r.get("name", r["key"]), r["domain_key"])
            for r in raw.get("artifact_sets", [])},
        steps={key: [UpgradeStepCost(s["component"], int(s["from_value"]), int(s["to_value"]), tuple(s["requirements"]))
                     for s in records] for key, records in (raw.get("steps") or {}).items()},
    )
