import pytest

from projectg.domain.targets.presets import TargetPresetViolation, next_preset_key
from projectg.domain.targets.validation import TargetValidationViolation, validate_target


def _target():
    return {
        "level": 80,
        "ascension": 5,
        "importance": {"level": 0.8, "ascension": 0.8},
        "talents": {
            name: {"enabled": False, "target": 1, "importance": 0.0}
            for name in ("normal", "skill", "burst")
        },
        "weapon": {"targetLevel": 90, "importance": 0.5, "weaponKey": "FutureWeapon"},
        "artifact": {
            "enabled": True,
            "targetQuality": "GOOD",
            "importance": 0.4,
            "primarySets": ["GoldenTroupe"],
            "alternativeSets": [],
            "gate": {"minLevel": 80, "requiredTalents": []},
        },
        "notes": "test",
    }


def test_validate_target_normalizes_shape_without_consulting_gamedata():
    result = validate_target(_target())

    assert result["weapon"]["weaponKey"] == "FutureWeapon"
    assert result["artifact"]["gate"]["minLevel"] == 80


def test_validate_target_reports_precise_shape_field():
    target = _target()
    target["talents"]["skill"]["enabled"] = 1

    with pytest.raises(TargetValidationViolation) as error:
        validate_target(target)

    assert error.value.field == "talents.skill.enabled"


def test_preset_key_policy_normalizes_and_avoids_collisions():
    label, key = next_preset_key("  On field  ", {"on-field", "on-field-2"})

    assert label == "On field"
    assert key == "on-field-3"


def test_preset_key_policy_rejects_blank_label():
    with pytest.raises(TargetPresetViolation):
        next_preset_key("   ", set())
