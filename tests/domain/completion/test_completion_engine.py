from projectg.domain.completion import evaluate_completion
from projectg.domain.planning.models import CharacterState, WeaponState


def target(*, artifact_enabled=False, weapon_key="Sword"):
    return {
        "level": 90,
        "ascension": 6,
        "talents": {
            "normal": {"enabled": False, "target": 1},
            "skill": {"enabled": True, "target": 10},
            "burst": {"enabled": True, "target": 10},
        },
        "weapon": {"weaponKey": weapon_key, "targetLevel": 90},
        "artifact": {"enabled": artifact_enabled, "targetQuality": "GOOD"},
    }


def state(*, weapon_key="Sword"):
    return CharacterState("A", 90, 6, {"auto": 1, "skill": 10, "burst": 10},
                          WeaponState("w", weapon_key, 90, 6))


def test_completion_engine_reports_all_terminal_states():
    assert evaluate_completion(state(), target()).status == "complete"
    mismatch = evaluate_completion(state(weapon_key="OtherSword"), target())
    assert mismatch.status == "incomplete"
    assert mismatch.components["weapon"]["reason"] == "weapon_mismatch"
    assert evaluate_completion(state(), target(artifact_enabled=True)).status == "unknown"

    invalid = target()
    invalid["level"] = 91
    assert evaluate_completion(state(), invalid).status == "invalid_target"


def test_missing_character_or_equipped_weapon_is_unknown():
    assert evaluate_completion(None, target()).status == "unknown"
    without_weapon = state()
    without_weapon.weapon = None
    assert evaluate_completion(without_weapon, target()).status == "unknown"
