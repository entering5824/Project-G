from collections import Counter

from projectg.domain.account.models import ArtifactState, NormalizedGood, WeaponState


_EVENT_ORDER = {
    "CHARACTER_ACQUIRED": 0,
    "CHARACTER_LEVEL_CHANGED": 1,
    "CHARACTER_ASCENSION_CHANGED": 2,
    "CONSTELLATION_CHANGED": 3,
    "TALENT_AUTO_CHANGED": 4,
    "TALENT_SKILL_CHANGED": 5,
    "TALENT_BURST_CHANGED": 6,
    "WEAPON_CHANGED": 7,
    "WEAPON_LEVEL_CHANGED": 8,
    "WEAPON_ASCENSION_CHANGED": 9,
    "WEAPON_REFINEMENT_CHANGED": 10,
    "ARTIFACT_LOADOUT_CHANGED": 11,
    "ARTIFACT_PIECE_CHANGED": 12,
    "TEAM_CHANGED": 13,
}


def compare_account_snapshots(
    before: NormalizedGood | None,
    after: NormalizedGood,
    *,
    from_snapshot_id: str | None,
    to_snapshot_id: str,
) -> dict:
    """Compare normalized account states without depending on persistence rows."""
    old_characters = {item.key: item for item in (before.characters if before else [])}
    new_characters = {item.key: item for item in after.characters}
    old_weapons = {item.instance_id: item for item in (before.weapons if before else [])}
    new_weapons = {item.instance_id: item for item in after.weapons}
    old_loadouts = _artifact_loadouts(before.artifacts if before else [])
    new_loadouts = _artifact_loadouts(after.artifacts)
    changes: list[dict] = []

    def add(kind: str, character_key: str | None, payload: dict) -> None:
        changes.append(
            {
                "eventType": kind,
                "source": "SNAPSHOT",
                "characterKey": character_key,
                "payload": payload,
                "snapshotId": to_snapshot_id,
            }
        )

    for key in sorted(new_characters.keys() - old_characters.keys()):
        current = new_characters[key]
        add(
            "CHARACTER_ACQUIRED",
            key,
            {
                "to": {
                    "level": current.level,
                    "ascension": current.ascension,
                    "constellation": current.constellation,
                }
            },
        )

    field_events = (
        ("level", "CHARACTER_LEVEL_CHANGED"),
        ("ascension", "CHARACTER_ASCENSION_CHANGED"),
        ("constellation", "CONSTELLATION_CHANGED"),
        ("talent_auto", "TALENT_AUTO_CHANGED"),
        ("talent_skill", "TALENT_SKILL_CHANGED"),
        ("talent_burst", "TALENT_BURST_CHANGED"),
    )
    for key in sorted(old_characters.keys() & new_characters.keys()):
        old = old_characters[key]
        new = new_characters[key]
        for field, event_type in field_events:
            start = getattr(old, field)
            end = getattr(new, field)
            if start != end:
                add(event_type, key, {"from": start, "to": end})

        old_instance = old.equipped_weapon_instance_id
        new_instance = new.equipped_weapon_instance_id
        old_weapon = old_weapons.get(old_instance)
        new_weapon = new_weapons.get(new_instance)
        if old_instance != new_instance:
            add(
                "WEAPON_CHANGED",
                key,
                {"from": _weapon_summary(old_weapon), "to": _weapon_summary(new_weapon)},
            )
        elif old_weapon and new_weapon:
            for field, event_type in (
                ("level", "WEAPON_LEVEL_CHANGED"),
                ("ascension", "WEAPON_ASCENSION_CHANGED"),
                ("refinement", "WEAPON_REFINEMENT_CHANGED"),
            ):
                start = getattr(old_weapon, field)
                end = getattr(new_weapon, field)
                if start != end:
                    add(
                        event_type,
                        key,
                        {
                            "weaponKey": new_weapon.key,
                            "instanceId": new_instance,
                            "from": start,
                            "to": end,
                        },
                    )

        if old_loadouts.get(key, ()) != new_loadouts.get(key, ()):
            add(
                "ARTIFACT_LOADOUT_CHANGED",
                key,
                {
                    "beforeCount": len(old_loadouts.get(key, ())),
                    "afterCount": len(new_loadouts.get(key, ())),
                },
            )
            old_by_slot = {item["slotKey"]: item for item in old_loadouts.get(key, ())}
            new_by_slot = {item["slotKey"]: item for item in new_loadouts.get(key, ())}
            for slot in sorted(old_by_slot.keys() | new_by_slot.keys()):
                before_piece = old_by_slot.get(slot)
                after_piece = new_by_slot.get(slot)
                if before_piece != after_piece:
                    add(
                        "ARTIFACT_PIECE_CHANGED",
                        key,
                        {"slotKey": slot, "from": before_piece, "to": after_piece},
                    )

    old_teams = _teams(before) if before else {}
    new_teams = _teams(after)
    if old_teams != new_teams:
        add(
            "TEAM_CHANGED",
            None,
            {"before": _team_payload(old_teams), "after": _team_payload(new_teams)},
        )

    changes.sort(
        key=lambda row: (
            row["characterKey"] or "",
            _EVENT_ORDER[row["eventType"]],
            row["payload"].get("materialKey", ""),
        )
    )
    return {
        "fromSnapshotId": from_snapshot_id,
        "toSnapshotId": to_snapshot_id,
        "summary": _summary(changes),
        "changes": changes,
    }


def _artifact_loadouts(artifacts: list[ArtifactState]) -> dict[str, tuple[dict, ...]]:
    grouped: dict[str, list[dict]] = {}
    for item in sorted(
        artifacts,
        key=lambda value: (value.character_key, value.slot_key, value.instance_id),
    ):
        grouped.setdefault(item.character_key, []).append(
            {
                "instanceId": item.instance_id,
                "setKey": item.set_key,
                "slotKey": item.slot_key,
                "rarity": item.rarity,
                "level": item.level,
                "mainStatKey": item.main_stat_key,
                "substats": item.substats or [],
                "unactivatedSubstats": item.unactivated_substats or [],
                "rv": item.rv,
                "rvStatus": item.rv_status,
                "rvFormulaVersion": item.rv_formula_version,
            }
        )
    return {key: tuple(value) for key, value in grouped.items()}


def _teams(snapshot: NormalizedGood) -> dict[str, tuple]:
    return {
        row.team_id: (row.name, tuple(sorted(row.members or [])))
        for row in snapshot.teams
    }


def _weapon_summary(weapon: WeaponState | None):
    if weapon is None:
        return None
    return {
        "instanceId": weapon.instance_id,
        "key": weapon.key,
        "level": weapon.level,
        "ascension": weapon.ascension,
        "refinement": weapon.refinement,
    }


def _team_payload(teams: dict[str, tuple]):
    return [
        {"teamId": key, "name": data[0], "members": list(data[1])}
        for key, data in sorted(teams.items())
    ]


def _summary(changes: list[dict]) -> dict:
    types = Counter(row["eventType"] for row in changes)
    characters = len({row["characterKey"] for row in changes if row["characterKey"]})
    return {
        "totalChanges": len(changes),
        "charactersChanged": characters,
        "charactersAcquired": types["CHARACTER_ACQUIRED"],
        "charactersLeveled": types["CHARACTER_LEVEL_CHANGED"],
        "ascensionsChanged": types["CHARACTER_ASCENSION_CHANGED"],
        "talentsUpgraded": sum(
            types[key]
            for key in (
                "TALENT_AUTO_CHANGED",
                "TALENT_SKILL_CHANGED",
                "TALENT_BURST_CHANGED",
            )
        ),
        "weaponsChanged": types["WEAPON_CHANGED"],
        "weaponsUpgraded": sum(
            types[key]
            for key in (
                "WEAPON_LEVEL_CHANGED",
                "WEAPON_ASCENSION_CHANGED",
                "WEAPON_REFINEMENT_CHANGED",
            )
        ),
        "artifactLoadoutsChanged": types["ARTIFACT_LOADOUT_CHANGED"],
        "artifactPiecesChanged": types["ARTIFACT_PIECE_CHANGED"],
        "teamsChanged": types["TEAM_CHANGED"],
    }
