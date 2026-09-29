"""Adapters from canonical AccountSnapshot values to existing persistence import."""

from __future__ import annotations

import json
from typing import Any

from projectg.domain.game_catalog.models import GameData
from projectg.interface_adapters.mappers.snapshot import SLOTS, SnapshotValidationError, parse_snapshot


def _token(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


def _index(values):
    result = {}
    for key, row in values.items():
        result[_token(key)] = key
        name = getattr(row, "name", None)
        if name:
            result[_token(name)] = key
    return result


def snapshot_to_good(value: str | bytes | dict[str, Any], game: GameData) -> tuple[bytes, dict[str, Any]]:
    snapshot, report = parse_snapshot(value)
    characters_by_name = _index(game.characters)
    weapons_by_name = _index(game.weapons)
    sets_by_name = _index(game.artifact_sets)
    characters, weapons, artifacts = [], [], []
    for key, char in snapshot["characters"].items():
        canonical_character = characters_by_name.get(_token(key))
        if canonical_character is None:
            report["warnings"].append(f"{key}: character identity is not in the installed GameData; skipped")
            report["unmapped"].append(key)
            continue
        key = canonical_character
        weapon = char["weapon"]
        weapon_id = f"snapshot-weapon-{key}"
        characters.append({"key": key, "level": char["level"], "ascension": char["ascension"],
            "constellation": char["constellation"], "talent": {
                "auto": char["talents"]["normal"], "skill": char["talents"]["skill"],
                "burst": char["talents"]["burst"]},
            "weapon": {"id": weapon_id} if weapon else None})
        if weapon:
            weapon_key = weapons_by_name.get(_token(weapon["key"]))
            if weapon_key is None:
                report["warnings"].append(f"{key}: weapon '{weapon['key']}' is not in installed GameData")
                weapon_key = weapon["key"]
            weapons.append({"id": weapon_id, "key": weapon_key, "level": weapon["level"],
                "ascension": weapon["ascension"], "refinement": weapon["refinement"], "location": key})
        for slot in SLOTS:
            item = char["artifacts"].get(slot)
            if item is None:
                continue
            set_key = sets_by_name.get(_token(item["setKey"]))
            if set_key is None:
                report["warnings"].append(f"{key}: artifact set '{item['setKey']}' is not in installed GameData")
                set_key = item["setKey"]
            artifacts.append({"id": f"snapshot-artifact-{key}-{slot}", "location": key,
                "setKey": set_key, "slotKey": slot, "rarity": 5,
                "level": item["level"], "mainStatKey": item.get("mainStat") or "unknown",
                "substats": [], "rv": item["rv"]})
    if not characters:
        raise SnapshotValidationError(["no character identity could be mapped to the installed GameData pack"])
    document = {"format": "GOOD", "version": 1, "dbVersion": 1,
                "characters": characters, "weapons": weapons, "artifacts": artifacts}
    return json.dumps(document, ensure_ascii=False).encode("utf-8"), report
