from projectg.domain.artifacts.rv import FORMULA_VERSION, calculate_piece_rv


def test_calculates_current_five_star_roll_value():
    substats = [
        {"key": "critRate_", "value": 15.56},  # four max rolls
        {"key": "critDMG_", "value": 15.54},  # two max rolls
        {"key": "atk_", "value": 5.83},       # one max roll
        {"key": "enerRech_", "value": 12.96}, # two max rolls
    ]

    rv, status = calculate_piece_rv(substats, rarity=5, level=20)

    assert (rv, status) == (900.0, "CALCULATED")
    assert FORMULA_VERSION == "artifact-rv-1"


def test_missing_or_impossible_substat_values_remain_unknown():
    assert calculate_piece_rv([], rarity=5, level=20) == (None, "UNKNOWN")
    assert calculate_piece_rv([
        {"key": "critRate_", "value": 99.0},
        {"key": "critDMG_", "value": 7.8},
        {"key": "atk_", "value": 5.8},
    ], rarity=5, level=20) == (None, "UNKNOWN")


def test_boolean_is_not_a_numeric_substat_value():
    assert calculate_piece_rv([
        {"key": "critRate_", "value": True},
        {"key": "critDMG_", "value": 7.8},
        {"key": "atk_", "value": 5.8},
    ], rarity=5, level=20) == (None, "UNKNOWN")
