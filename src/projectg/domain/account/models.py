from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(frozen=True)
class CharacterState:
    key: str
    level: int
    ascension: int
    constellation: int
    talent_auto: int
    talent_skill: int
    talent_burst: int
    equipped_weapon_instance_id: str | None = None

@dataclass(frozen=True)
class WeaponState:
    instance_id: str
    key: str
    level: int
    ascension: int
    refinement: int
    location: str | None = None

@dataclass(frozen=True)
class ArtifactState:
    instance_id: str
    character_key: str
    set_key: str
    slot_key: str
    rarity: int
    level: int
    main_stat_key: str
    substats: list[dict[str, Any]] = field(default_factory=list)
    unactivated_substats: list[dict[str, Any]] = field(default_factory=list)
    rv: float | None = None
    rv_status: str = "UNKNOWN"
    rv_formula_version: str = "artifact-rv-1"

@dataclass(frozen=True)
class TeamState:
    team_id: str
    name: str | None
    members: list[Any]
    raw_config: dict[str, Any] | None = None

@dataclass(frozen=True)
class NormalizedGood:
    good_format: str
    good_version: int | None
    good_db_version: int | None
    characters: list[CharacterState]
    weapons: list[WeaponState]
    artifacts: list[ArtifactState]
    teams: list[TeamState]
    warnings: list[str] = field(default_factory=list)
    coverage: dict[str, bool] = field(default_factory=dict)

    def canonical_state(self) -> dict[str, Any]:
        return {
            "characters": [asdict(x) for x in sorted(self.characters, key=lambda x: x.key)],
            "weapons": [asdict(x) for x in sorted(self.weapons, key=lambda x: x.instance_id)],
            "artifacts": [asdict(x) for x in sorted(self.artifacts, key=lambda x: (x.character_key, x.slot_key, x.instance_id))],
            "teams": [asdict(x) for x in sorted(self.teams, key=lambda x: x.team_id)],
        }
