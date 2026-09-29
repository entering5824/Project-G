from collections.abc import Iterable

from projectg.domain.account.models import CharacterState, NormalizedGood, WeaponState


CHARACTER_FIELDS = (
    ("level", "level"),
    ("ascension", "ascension"),
    ("constellation", "constellation"),
    ("talent_auto", "normal"),
    ("talent_skill", "skill"),
    ("talent_burst", "burst"),
)
WEAPON_FIELDS = (
    ("level", "level"),
    ("ascension", "ascension"),
    ("refinement", "refinement"),
)


def detect_progression_regressions(
    previous_characters: Iterable[CharacterState],
    previous_weapons: Iterable[WeaponState],
    incoming: NormalizedGood,
) -> list[dict]:
    """Detect decreases in observed account progression between snapshots."""
    previous_character_map = {character.key: character for character in previous_characters}
    previous_weapon_map = {weapon.instance_id: weapon for weapon in previous_weapons}
    changes: list[dict] = []

    incoming_keys = {character.key for character in incoming.characters}
    for missing_key in sorted(previous_character_map.keys() - incoming_keys):
        changes.append(
            {
                "characterKey": missing_key,
                "field": "owned character",
                "before": "present",
                "after": "missing",
            }
        )

    for character in incoming.characters:
        old = previous_character_map.get(character.key)
        if old is None:
            continue
        for attribute, label in CHARACTER_FIELDS:
            before = getattr(old, attribute)
            after = getattr(character, attribute)
            if before is not None and after is not None and after < before:
                changes.append(
                    {
                        "characterKey": character.key,
                        "field": label,
                        "before": before,
                        "after": after,
                    }
                )

    for weapon in incoming.weapons:
        old = previous_weapon_map.get(weapon.instance_id)
        if old is None:
            continue
        for attribute, label in WEAPON_FIELDS:
            before = getattr(old, attribute)
            after = getattr(weapon, attribute)
            if before is not None and after is not None and after < before:
                changes.append(
                    {
                        "characterKey": weapon.location or weapon.instance_id,
                        "field": f"weapon {label}",
                        "before": before,
                        "after": after,
                        "weaponInstanceId": weapon.instance_id,
                    }
                )

    return changes
