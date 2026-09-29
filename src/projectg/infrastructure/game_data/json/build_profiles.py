"""Versioned build-profile JSON loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_STATUSES = {"VERIFIED", "PROVISIONAL", "STALE"}
VALID_DEPTHS = {"BASIC", "STANDARD", "DEEP"}

from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack


def load_build_pack(path: Path, *, character_keys: set[str] | None = None) -> BuildKnowledgePack:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return BuildKnowledgePack("unknown", "unknown", {}, (str(exc),), {"profiled": 0, "missing": sorted(character_keys or ())})
    errors: list[str] = []
    profiles: dict[str, list[dict[str, Any]]] = {}
    if value.get("schemaVersion") != 1 or not isinstance(value.get("profiles"), list):
        errors.append("schemaVersion must be 1 and profiles must be an array")
        rows = []
    else:
        rows = value["profiles"]
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"profiles[{index}] must be an object")
            continue
        key, profile_id = row.get("characterKey"), row.get("id")
        if not isinstance(key, str) or not isinstance(profile_id, str):
            errors.append(f"profiles[{index}] needs characterKey and id")
            continue
        compound = f"{key}:{profile_id}"
        if compound in seen:
            errors.append(f"duplicate profile {compound}")
            continue
        seen.add(compound)
        if row.get("status") not in VALID_STATUSES or row.get("depth") not in VALID_DEPTHS:
            errors.append(f"{compound} has invalid status or depth")
            continue
        if not isinstance(row.get("sources"), list) or not row["sources"]:
            errors.append(f"{compound} must include provenance")
            continue
        if not isinstance(row.get("archetype"), str) or not row["archetype"].strip():
            errors.append(f"{compound} must include archetype")
            continue
        if any(not isinstance(source, dict) or any(not isinstance(source.get(field), str) or not source[field]
               for field in ("type", "url", "checkedGameVersion")) for source in row["sources"]):
            errors.append(f"{compound} has incomplete source provenance")
            continue
        progression = row.get("progression")
        if not isinstance(progression, dict):
            errors.append(f"{compound} must include progression")
            continue
        try:
            level = int(progression["level"])
            talents = progression["talents"]
            weapon = progression["weapon"]
            if level < 1 or level > 90 or not isinstance(talents, dict) or not isinstance(weapon, dict):
                raise ValueError
            if any(not isinstance(talents.get(name), dict) or
                   not 1 <= int(talents[name]["target"]) <= 13
                   for name in ("normal", "skill", "burst")):
                raise ValueError
            if not 1 <= int(weapon["targetLevel"]) <= 90:
                raise ValueError
            for component in [weapon, *(talents.get(name, {}) for name in ("normal", "skill", "burst"))]:
                curve = component.get("stepUtility") or {}
                if not isinstance(curve, dict) or any(type(value) not in (int, float) or not 0 <= value <= 1
                                                      for value in curve.values()):
                    raise ValueError
        except (KeyError, TypeError, ValueError):
            errors.append(f"{compound} has invalid progression targets")
            continue
        profiles.setdefault(key, []).append(row)
    eligible_keys = character_keys if character_keys is not None else set(profiles)
    missing = sorted(eligible_keys - profiles.keys())
    stale = sorted(f"{key}:{row['id']}" for key, rows_for_char in profiles.items()
                   for row in rows_for_char if row["status"] == "STALE")
    basic = {key for key, rows_for_char in profiles.items()
             if any(row["depth"] == "BASIC" and row["status"] == "VERIFIED" for row in rows_for_char)}
    standard = {key for key, rows_for_char in profiles.items()
                if any(row["depth"] in {"STANDARD", "DEEP"} and row["status"] == "VERIFIED" for row in rows_for_char)}
    deep = {key for key, rows_for_char in profiles.items()
            if any(row["depth"] == "DEEP" and row["status"] == "VERIFIED" for row in rows_for_char)}
    verified_basic_count = len(basic & eligible_keys)
    verified_standard_count = len(standard & eligible_keys)
    verified_deep_count = len(deep & eligible_keys)
    basic_coverage_ready = (not missing and not stale
                            and verified_basic_count == len(eligible_keys))
    advanced_coverage_ready = (verified_standard_count >= 50
                               and 20 <= verified_deep_count <= 30)
    coverage = {"characters": len(eligible_keys), "profiled": len(set(profiles) & eligible_keys),
        "verifiedBasic": verified_basic_count, "verifiedStandard": verified_standard_count,
        "verifiedDeep": verified_deep_count, "minimumStandard": 50,
        "targetDeep": {"minimum": 20, "maximum": 30}, "missing": missing, "stale": stale,
        # A complete Basic layer is sufficient to make useful account-wide
        # progression recommendations. Standard/Deep are additional research
        # coverage and must not disable the already-complete baseline planner.
        "recommendationsReady": basic_coverage_ready,
        "advancedCoverageReady": advanced_coverage_ready,
        "releaseReady": basic_coverage_ready and advanced_coverage_ready}
    return BuildKnowledgePack(str(value.get("packVersion", "unknown")), str(value.get("gameVersion", "unknown")),
                     profiles, tuple(errors), coverage)

