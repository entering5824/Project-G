from projectg.domain.account.models import CharacterState, NormalizedGood, WeaponState
from projectg.domain.account.regression import detect_progression_regressions


def test_detect_progression_regressions_is_pure_domain_policy():
    previous_characters = [CharacterState("amber", 80, 5, 2, 6, 8, 8, "w1")]
    previous_weapons = [WeaponState("w1", "FavoniusBow", 80, 5, 3, "amber")]
    incoming = NormalizedGood(
        "GOOD",
        1,
        1,
        [CharacterState("amber", 70, 5, 2, 6, 7, 8, "w1")],
        [WeaponState("w1", "FavoniusBow", 70, 5, 2, "amber")],
        [],
        [],
    )

    changes = detect_progression_regressions(previous_characters, previous_weapons, incoming)

    assert {change["field"] for change in changes} == {
        "level",
        "skill",
        "weapon level",
        "weapon refinement",
    }
