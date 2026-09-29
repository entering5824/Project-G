import pytest

from projectg.domain.targets.rules import TargetRuleViolation, validate_target_rules


def _target():
    return {
        "level": 80,
        "ascension": 6,
        "importance": {"level": 1.0, "ascension": 0.7},
        "talents": {
            "normal": {"enabled": True, "target": 8, "importance": 0.3},
            "skill": {"enabled": True, "target": 10, "importance": 0.8},
            "burst": {"enabled": False, "target": 1, "importance": 0.5},
        },
        "weapon": {"targetLevel": 90, "importance": 0.5},
        "artifact": {
            "importance": 0.5,
            "gate": {"minLevel": 80, "minAscension": 6, "requiredTalents": ["skill"]},
        },
    }


def test_target_rules_accept_reachable_progression():
    validate_target_rules(_target())


def test_target_rules_reject_impossible_talent_and_disabled_gate():
    target = _target()
    target["ascension"] = 4
    target["level"] = 60
    target["talents"]["skill"]["target"] = 9
    target["artifact"]["gate"]["requiredTalents"] = ["burst"]

    with pytest.raises(TargetRuleViolation) as error:
        validate_target_rules(target)

    assert error.value.field == "talents.skill.target"
