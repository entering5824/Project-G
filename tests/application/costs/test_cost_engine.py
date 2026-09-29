import json

import pytest

from projectg.domain.costs.models import CostStatus
from projectg.domain.costs.resolver import resolve_cost, resolve_requirements
from projectg.domain.game_catalog.validation import GameDataValidationError, validate_game_data
from projectg.domain.planning.models import GoalType, UpgradeGoal
from projectg.infrastructure.game_data.json.loader import DATASET, load_game_data
from projectg.infrastructure.game_data.json.normalization import normalize_game_data
from projectg.domain.costs.engine import CostEngine


@pytest.fixture(scope="module")
def game():
    return load_game_data(DATASET, strict=True)


def goal(kind, char="Aloy", current=1, target=10, weapon=None):
    return UpgradeGoal(
        "id",
        f"{char}:{kind.value}",
        char,
        kind,
        current,
        target,
        1,
        1,
        1,
        1,
        0,
        weapon_key=weapon,
        strategic_target=target,
        next_milestone=target,
    )


def test_dataset_metadata_and_catalog_are_valid(game):
    assert game.metadata["schema_version"] == 1
    assert len(game.materials) > 30


def test_duplicate_stable_keys_rejected(tmp_path):
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    raw["materials"].append(dict(raw["materials"][0]))
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate materials"):
        load_game_data(path, strict=True)


def test_broken_reference_and_missing_step_fail_validation():
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    raw["domains"][0]["reward_material_families"].append("NoSuchFamily")
    raw["steps"]["character_level"][2]["from_value"] = 49
    with pytest.raises(GameDataValidationError) as error:
        validate_game_data(normalize_game_data(raw))
    codes = {item["code"] for item in error.value.problems}
    assert "UNKNOWN_DOMAIN_REWARD" in codes
    assert "COST_PATH_GAP" in codes


def test_zero_cost_when_current_is_at_or_above_target(game):
    same = goal(GoalType.TALENT_SKILL, current=8, target=8)
    assert resolve_requirements(game, same, 8) == {}
    above = goal(GoalType.CHARACTER_LEVEL, current=40, target=20)
    assert resolve_requirements(game, above, 20) == {}


def test_character_and_talent_paths_sum_steps(game):
    character = goal(GoalType.CHARACTER_LEVEL, "Aloy", 20, 40)
    assert resolve_requirements(game, character, 40) == {"CharacterEXP": 578325, "Mora": 115800}
    talent = goal(GoalType.TALENT_SKILL, "Aloy", 8, 10)
    assert resolve_requirements(game, talent, 10) == {
        "PhilosophiesOfFreedom": 28,
        "SpectralNucleus": 21,
        "MoltenMoment": 4,
        "CrownOfInsight": 1,
        "Mora": 1150000,
    }


def test_weapon_rarity_path_and_impossible_max_level(game):
    weapon = goal(GoalType.WEAPON_LEVEL, "Barbara", 1, 40, "ThrillingTalesOfDragonSlayers")
    assert resolve_requirements(game, weapon, 40) == {
        "WeaponEXP": 327475,
        "Mora": 37760,
        "BorealWolfsMilkTooth": 2,
        "DeadLeyLineBranch": 2,
        "DiviningScroll": 1,
    }
    impossible = goal(GoalType.WEAPON_LEVEL, "Amber", 1, 90, "HuntersBow")
    assert resolve_requirements(game, impossible, 90) is None


def test_weapon_level_cost_adds_exact_ascension_path_when_pack_provides_it():
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    raw["steps"]["weapon_ascension:ThrillingTalesOfDragonSlayers"] = [
        {
            "component": "WEAPON_ASCENSION",
            "from_value": 0,
            "to_value": 1,
            "requirements": [
                {"material_key": "TileOfDecarabiansTower", "amount": 5},
                {"material_key": "Mora", "amount": 5000},
            ],
        },
    ]
    enriched = normalize_game_data(raw)
    validate_game_data(enriched)
    weapon = goal(GoalType.WEAPON_LEVEL, "Barbara", 1, 40, "ThrillingTalesOfDragonSlayers")
    weapon.weapon_ascension = 0
    requirements = resolve_requirements(enriched, weapon, 40)
    assert requirements["WeaponEXP"] == 327475
    assert requirements["TileOfDecarabiansTower"] == 5
    assert requirements["Mora"] == 37760


def test_cost_projection_is_theoretical_and_does_not_consume_inventory(game):
    requirements = {"WeatheredArrowhead": 3, "Mora": 100}
    result = resolve_cost(game, requirements)

    assert result.required_cost == requirements
    assert result.status == CostStatus.ESTIMATED
    assert requirements == {"WeatheredArrowhead": 3, "Mora": 100}


def test_weekly_and_non_farmable_semantics_do_not_require_inventory(game):
    assert resolve_cost(game, {}).status == CostStatus.ESTIMATED
    assert resolve_cost(game, {"Mora": 10}).status == CostStatus.ESTIMATED
    crown = resolve_cost(game, {"CrownOfInsight": 1})
    assert crown.status == CostStatus.ESTIMATED
    weekly = resolve_cost(game, {"RingOfBoreas": 1})
    assert weekly.status == CostStatus.ESTIMATED


def test_cost_service_projects_targets_without_database_inventory(game):
    character = goal(GoalType.CHARACTER_LEVEL, "Aloy", 20, 40)
    projected = CostEngine(game).cost_for_goal(character)

    assert projected["fullCost"]["requiredCost"] == {"CharacterEXP": 578325, "Mora": 115800}
    assert "missing" not in projected["fullCost"]
    assert projected["fullCost"]["status"] == CostStatus.ESTIMATED
    assert "owned" not in projected["fullCost"]
