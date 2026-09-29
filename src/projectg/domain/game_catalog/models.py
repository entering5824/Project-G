from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Material:
    key: str
    name: str
    category: str
    rarity: int | None = None
    family_key: str | None = None
    tier: int | None = None
    craft_recipe: dict[str, Any] | None = None
    farmable: bool = True
    source: dict[str, Any] | None = None
    exp_value: int | None = None


@dataclass(frozen=True)
class CharacterDefinition:
    key: str
    rarity: int
    element: str
    weapon_type: str
    region: str
    local_specialty: str
    normal_boss_material: str | None
    enemy_material_family: str
    talent_book_family: str
    weekly_boss_materials: tuple[str, ...]
    gem_family: str | None = None
    material_keys: dict[str, str] = field(default_factory=dict)
    name: str | None = None


@dataclass(frozen=True)
class WeaponDefinition:
    key: str
    name: str
    rarity: int
    weapon_type: str
    weapon_ascension_material_family: str | None
    enemy_material_family: str | None
    max_level: int = 90


@dataclass(frozen=True)
class DomainDefinition:
    key: str
    type: str
    reward_material_families: tuple[str, ...]
    schedule_group: str | None = None
    name: str | None = None
    resin_cost: int = 20


@dataclass(frozen=True)
class BossDefinition:
    key: str
    reward_materials: tuple[str, ...]
    resin_cost: int
    weekly_limited: bool
    name: str | None = None


@dataclass(frozen=True)
class ArtifactSetDefinition:
    key: str
    name: str
    domain_key: str


@dataclass(frozen=True)
class UpgradeStepCost:
    component: str
    from_value: int
    to_value: int
    requirements: tuple[dict[str, Any], ...]


@dataclass
class GameData:
    metadata: dict[str, Any]
    characters: dict[str, CharacterDefinition] = field(default_factory=dict)
    weapons: dict[str, WeaponDefinition] = field(default_factory=dict)
    materials: dict[str, Material] = field(default_factory=dict)
    domains: dict[str, DomainDefinition] = field(default_factory=dict)
    bosses: dict[str, BossDefinition] = field(default_factory=dict)
    artifact_sets: dict[str, ArtifactSetDefinition] = field(default_factory=dict)
    steps: dict[str, list[UpgradeStepCost]] = field(default_factory=dict)
    error: dict[str, Any] | None = None
