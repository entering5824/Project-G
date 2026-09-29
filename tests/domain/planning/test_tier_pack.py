import pytest

from projectg.domain.planning.tier_pack import tier_pack_content, validate_tier_pack


def test_tier_pack_validation_normalizes_notes_and_defaults():
    result = validate_tier_pack(
        {"version": 1, "ratings": {"Amber": {"score": 67, "notes": "  test  "}}},
        known_keys={"Amber"},
        known_sets={"SetA"},
    )

    assert result == {
        "version": 1,
        "ratings": {"Amber": {"score": 67, "notes": "test"}},
        "minimumTierForRoadmap": "B",
        "controls": {},
        "selectedSets": {},
    }
    assert tier_pack_content({**result, "packVersion": 9}) == result


def test_tier_pack_validation_rejects_unknown_character_and_set():
    with pytest.raises(ValueError, match="Unknown character"):
        validate_tier_pack(
            {"version": 1, "ratings": {"Future": {"score": 10}}},
            known_keys={"Amber"}, known_sets={"SetA"},
        )
    with pytest.raises(ValueError, match="selectedSets"):
        validate_tier_pack(
            {"version": 1, "ratings": {}, "selectedSets": {"Amber": "UnknownSet"}},
            known_keys={"Amber"}, known_sets={"SetA"},
        )
