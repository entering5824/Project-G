"""Adapter from GOOD interchange JSON into the application's domain state."""
import json
from math import isfinite
from typing import Any
from projectg.domain.game_catalog.models import GameData
from projectg.domain.account.models import ArtifactState, CharacterState, NormalizedGood, TeamState, WeaponState
from projectg.domain.artifacts.rv import FORMULA_VERSION, calculate_piece_rv

class GoodImportError(ValueError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}

def _domain_int(obj: dict, field: str, aliases: tuple[str, ...], minimum: int, maximum: int, default: int | None = 0) -> int | None:
    """Read a GOOD integer without coercion and reject out-of-domain values."""
    present_key = next((key for key in aliases if key in obj), None)
    if present_key is None:
        return default
    value = obj[present_key]
    if type(value) is not int or not minimum <= value <= maximum:
        raise GoodImportError(
            f"Invalid {field} value",
            {"field": field, "value": value, "expected": f"integer from {minimum} to {maximum}"},
        )
    return value

def _key(obj: dict, *keys: str) -> str | None:
    for k in keys:
        val = obj.get(k)
        if isinstance(val, str) and val: return val
    return None

def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)

def _token(value: str) -> str:
    return "".join(character.casefold() for character in value if character.isalnum())

def _normalized_location(location: Any, owned_keys: set[str]) -> str | None:
    if not isinstance(location, str) or not location: return None
    if location in owned_keys: return location
    # GOOD exports Traveler's equipment under the display alias "Traveler" while
    # the owned character key is element-qualified (for example, TravelerAnemo).
    if location == "Traveler":
        traveler_keys = [key for key in owned_keys if key.startswith("Traveler")]
        if len(traveler_keys) == 1: return traveler_keys[0]
    return location

class GoodImporter:
    version = "1"

    def __init__(self, game_data: GameData | None = None):
        self.game_data = game_data or GameData(metadata={})

    def validate(self, value: Any) -> list[str]:
        problems = []
        if not isinstance(value, dict): return ["GOOD document must be a JSON object"]
        if value.get("format") != "GOOD": problems.append("format must be GOOD")
        if "characters" in value and not isinstance(value.get("characters"), list): problems.append("characters must be a list when present")
        character_keys: set[str] = set()
        for section in ("weapons", "artifacts"):
            if section in value and not isinstance(value[section], list): problems.append(f"{section} must be a list when present")
            elif isinstance(value.get(section), list):
                for i, item in enumerate(value[section]):
                    if not isinstance(item, dict): problems.append(f"{section}[{i}] must be an object")
        if isinstance(value.get("characters"), list):
            character_key_list = []
            for i, c in enumerate(value["characters"]):
                if not isinstance(c, dict) or not _key(c, "key", "name", "characterKey"):
                    problems.append(f"characters[{i}] must be an object with a stable key")
                else:
                    character_key_list.append(_key(c, "key", "name", "characterKey"))
            duplicates = _duplicate_values(character_key_list)
            if duplicates:
                problems.append(f"character keys must be unique: {duplicates}")
            character_keys = set(character_key_list)
        for section, id_keys, prefix in (
            ("weapons", ("id", "instanceId"), "weapon"),
            ("artifacts", ("id", "instanceId"), "artifact"),
        ):
            items = value.get(section)
            if isinstance(items, list):
                identifiers = [
                    _key(item, *id_keys) or f"{prefix}-{i}"
                    for i, item in enumerate(items)
                    if isinstance(item, dict)
                ]
                duplicates = _duplicate_values(identifiers)
                if duplicates:
                    problems.append(f"{section} instance IDs must be unique: {duplicates}")
        if isinstance(value.get("artifacts"), list):
            for i, item in enumerate(value["artifacts"]):
                if not isinstance(item, dict):
                    continue
                substats = item.get("substats", [])
                unactivated = item.get("unactivatedSubstats", [])
                for field, stats in (("substats", substats), ("unactivatedSubstats", unactivated)):
                    if not isinstance(stats, list):
                        problems.append(f"artifacts[{i}].{field} must be a list")
                        continue
                    for j, stat in enumerate(stats):
                        stat_value = stat.get("value") if isinstance(stat, dict) else None
                        if (not isinstance(stat, dict) or not isinstance(stat.get("key"), str)
                                or type(stat_value) not in (int, float) or not isfinite(float(stat_value)) or stat_value < 0):
                            problems.append(f"artifacts[{i}].{field}[{j}] must have a string key and numeric value")
        teams = value.get("teams", value.get("savedTeams", []))
        if not isinstance(teams, list):
            problems.append("teams must be a list when present")
        else:
            for i, team in enumerate(teams):
                if not isinstance(team, dict):
                    problems.append(f"teams[{i}] must be an object")
                    continue
                member_field = "members" if "members" in team else "characters" if "characters" in team else None
                if member_field is None:
                    continue
                members = team[member_field]
                if not isinstance(members, list) or any(type(member) is not str or not member.strip() for member in members):
                    problems.append(f"teams[{i}].{member_field} must be a list of non-empty character keys")
                    continue
                duplicates = _duplicate_values(members)
                if duplicates:
                    problems.append(f"teams[{i}].{member_field} must be unique: {duplicates}")
                unknown = sorted(set(members) - character_keys)
                if unknown:
                    problems.append(f"teams[{i}].{member_field} references unknown characters: {unknown}")
        return problems

    def parse(self, raw: str | bytes | dict) -> dict:
        try:
            value = raw if isinstance(raw, dict) else json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise GoodImportError("Invalid JSON", {"problem": str(exc)}) from exc
        problems = self.validate(value)
        if problems: raise GoodImportError("Invalid GOOD document", {"problems": problems})
        return value

    def normalize(self, value: dict) -> NormalizedGood:
        value = self.parse(value)
        warnings: list[str] = []
        game = self.game_data
        character_index = {_token(key): key for key in game.characters}
        weapon_index = {}
        for key, definition in game.weapons.items():
            weapon_index[_token(key)] = key
            weapon_index[_token(definition.name)] = key
        set_index = {}
        for key, definition in game.artifact_sets.items():
            set_index[_token(key)] = key
            set_index[_token(definition.name)] = key
        aliases = {}
        for c in value.get("characters", []):
            source_key = _key(c, "key", "name", "characterKey")
            if not source_key:
                continue
            canonical = character_index.get(_token(source_key), source_key)
            aliases[_token(source_key)] = canonical
            if canonical == source_key and _token(source_key) not in character_index:
                warnings.append(f"Character '{source_key}' is not in installed GameData")
        owned_keys = set(aliases.values())
        weapons: list[WeaponState] = []
        weapon_by_id = {}
        for i, w in enumerate(value.get("weapons", [])):
            iid = _key(w, "id", "instanceId") or f"weapon-{i}"
            key = _key(w, "key", "name", "weaponKey") or f"UnknownWeapon-{iid}"
            canonical_weapon = weapon_index.get(_token(key))
            if canonical_weapon:
                key = canonical_weapon
            else:
                warnings.append(f"Weapon '{key}' is not in installed GameData")
            location = w.get("location")
            if isinstance(location, dict): location = _key(location, "key", "name", "characterKey")
            if isinstance(location, str):
                location = aliases.get(_token(location), location)
            location = _normalized_location(location, owned_keys)
            state = WeaponState(
                iid, key,
                _domain_int(w, "weapons.level", ("level",), 1, 90),
                _domain_int(w, "weapons.ascension", ("ascension", "ascensionLevel"), 0, 6),
                _domain_int(w, "weapons.refinement", ("refinement", "refine"), 1, 5, default=1),
                location,
            )
            weapons.append(state); weapon_by_id[iid] = state

        characters = []
        for c in value.get("characters", []):
            source_key = _key(c, "key", "name", "characterKey")
            assert source_key
            key = aliases.get(_token(source_key), source_key)
            talents = c.get("talent", c.get("talents", {}))
            if talents is None: talents = {}
            if not isinstance(talents, dict):
                raise GoodImportError("Invalid character talents", {"field": f"characters.{key}.talents", "expected": "object"})
            weapon = c.get("weapon")
            weapon_id = _key(weapon, "id", "instanceId") if isinstance(weapon, dict) else None
            # GOOD exports commonly encode a weapon's equipped character through location.
            if weapon_id is None:
                equipped = next((w.instance_id for w in weapons if w.location == key), None)
                weapon_id = equipped
            characters.append(CharacterState(
                key,
                _domain_int(c, f"characters.{key}.level", ("level",), 1, 100),
                _domain_int(c, f"characters.{key}.ascension", ("ascension", "ascensionLevel"), 0, 6),
                _domain_int(c, f"characters.{key}.constellation", ("constellation", "cons"), 0, 6),
                _domain_int(talents, f"characters.{key}.talent.auto", ("auto", "normal", "normalAttack"), 1, 15),
                _domain_int(talents, f"characters.{key}.talent.skill", ("skill", "elementalSkill"), 1, 15),
                _domain_int(talents, f"characters.{key}.talent.burst", ("burst", "elementalBurst"), 1, 15),
                weapon_id,
            ))

        artifacts = []
        for i, a in enumerate(value.get("artifacts", [])):
            rarity = _domain_int(a, f"artifacts[{i}].rarity", ("rarity",), 1, 5)
            level = _domain_int(a, f"artifacts[{i}].level", ("level",), 0, 20)
            loc = a.get("location")
            if isinstance(loc, dict): loc = _key(loc, "key", "name", "characterKey")
            if isinstance(loc, str):
                loc = aliases.get(_token(loc), loc)
            loc = _normalized_location(loc, owned_keys)
            if not isinstance(loc, str) or loc not in owned_keys: continue
            iid = _key(a, "id", "instanceId") or f"artifact-{i}"
            stats = a.get("substats", [])
            if not isinstance(stats, list): stats = []
            unactivated = a.get("unactivatedSubstats", [])
            if not isinstance(unactivated, list): unactivated = []
            supplied_rv = a.get("rv")
            if (type(supplied_rv) in (int, float) and isfinite(float(supplied_rv))
                    and supplied_rv >= 0):
                rv, rv_status = round(float(supplied_rv), 2), "IMPORTED"
            else:
                rv, rv_status = calculate_piece_rv(stats, rarity, level)
            source_set = _key(a, "setKey", "set", "name") or "UnknownSet"
            set_key = set_index.get(_token(source_set), source_set)
            if set_key == source_set and _token(source_set) not in set_index:
                warnings.append(f"Artifact set '{source_set}' is not in installed GameData")
            artifacts.append(ArtifactState(iid, loc, set_key, _key(a, "slotKey", "slot", "position") or "unknown", rarity, level, _key(a, "mainStatKey", "mainStat", "mainstat") or "unknown", stats, unactivated, rv, rv_status, FORMULA_VERSION))

        teams = []
        source = value.get("teams", value.get("savedTeams", []))
        raw_teamchars = value.get("teamchars", [])
        teamchar_items = raw_teamchars if isinstance(raw_teamchars, list) else []
        teamchars_by_id = {
            item.get("id"): item for item in teamchar_items
            if isinstance(item, dict) and item.get("id")
        }
        if isinstance(source, list):
            for i, t in enumerate(source):
                if isinstance(t, dict):
                    raw_config = t.get("config", t.get("rawConfig"))
                    if raw_config is None:
                        raw_config = {k: v for k, v in t.items() if k not in {"id", "teamId", "name", "members", "characters"}}
                    members = t.get("members", t.get("characters"))
                    loadout = t.get("loadoutData", [])
                    linked_teamchars = []
                    if isinstance(loadout, list):
                        for slot in loadout:
                            if isinstance(slot, dict):
                                teamchar = teamchars_by_id.get(slot.get("teamCharId"))
                                if teamchar:
                                    linked_teamchars.append(teamchar)
                    if members is None:
                        members = [_key(member, "key", "characterKey") or member.get("id") for member in linked_teamchars]
                        members = [member for member in members if member]
                    # GOOD keeps per-character team configuration in a separate teamchars section.
                    # Preserve each linked record verbatim alongside the team's loadout/conditional config.
                    if linked_teamchars:
                        if not isinstance(raw_config, dict): raw_config = {"config": raw_config}
                        raw_config = {**raw_config, "teamCharConfigs": linked_teamchars}
                    teams.append(TeamState(str(t.get("id", t.get("teamId", i))), t.get("name"), members if isinstance(members, list) else [], raw_config or None))
                else: warnings.append(f"Ignored malformed team at index {i}")
        good_version = _domain_int(value, "version", ("version",), 1, 2**31 - 1, default=None)
        db_version = _domain_int(value, "dbVersion", ("dbVersion", "goodDbVersion"), 1, 2**31 - 1, default=None)
        return NormalizedGood("GOOD", good_version, db_version, characters, weapons, artifacts, teams, warnings,
                              coverage={name: name in value or (name == "teams" and "savedTeams" in value)
                                        for name in ("characters", "weapons", "artifacts", "teams")})
