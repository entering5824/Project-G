"""AccountSnapshot v1 validation and normalization helpers."""

from __future__ import annotations

import json
from collections import Counter
from math import isfinite
from typing import Any

SLOTS = ("flower", "plume", "sands", "goblet", "circlet")


class SnapshotValidationError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Invalid AccountSnapshot: " + "; ".join(problems))


def parse_snapshot(value: str | bytes | dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a canonical snapshot and a non-fatal import report."""
    try:
        data = value if isinstance(value, dict) else json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise SnapshotValidationError([f"invalid JSON: {exc}"]) from exc
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("characters"), dict):
        raise SnapshotValidationError(["version must be 1 and characters must be an object"])
    problems: list[str] = []
    warnings: list[str] = []
    unmapped: list[str] = []
    canonical: dict[str, Any] = {"version": 1, "source": data.get("source", {"type": "MANUAL"}), "characters": {}}
    if not data["characters"]:
        problems.append("at least one character is required")
    for key, raw in data["characters"].items():
        prefix = f"characters.{key}"
        if not isinstance(key, str) or not key.strip() or not isinstance(raw, dict):
            warnings.append(f"{prefix} must be a named object; entry skipped")
            unmapped.append(str(key))
            continue
        try:
            level = _integer(raw.get("level"), 1, 100, f"{prefix}.level")
            ascension = _integer(raw.get("ascension", 6 if level == 90 else 0), 0, 6, f"{prefix}.ascension")
            constellation = _integer(raw.get("constellation", 0), 0, 6, f"{prefix}.constellation")
            talents = raw.get("talents")
            if not isinstance(talents, dict):
                raise ValueError(f"{prefix}.talents must be an object")
            normalized_talents = {name: _integer(talents.get(name), 1, 15, f"{prefix}.talents.{name}")
                                  for name in ("normal", "skill", "burst")}
            weapon = raw.get("weapon")
            if weapon is not None:
                if not isinstance(weapon, dict) or not isinstance(weapon.get("key"), str) or not weapon["key"].strip():
                    raise ValueError(f"{prefix}.weapon must be null or include a key")
                weapon = {"key": weapon["key"], "level": _integer(weapon.get("level"), 1, 90, f"{prefix}.weapon.level"),
                          "ascension": _integer(weapon.get("ascension", 6 if weapon.get("level") == 90 else 0), 0, 6, f"{prefix}.weapon.ascension"),
                          "refinement": _integer(weapon.get("refinement", 1), 1, 5, f"{prefix}.weapon.refinement")}
            artifacts = raw.get("artifacts", {})
            if not isinstance(artifacts, dict) or set(artifacts) - set(SLOTS):
                raise ValueError(f"{prefix}.artifacts contains an invalid slot")
            normalized_artifacts = {}
            for slot, item in artifacts.items():
                if not isinstance(item, dict) or not isinstance(item.get("setKey"), str) or not item["setKey"].strip():
                    raise ValueError(f"{prefix}.artifacts.{slot} must include setKey")
                rv = item.get("rv")
                if rv is not None and (type(rv) not in (int, float) or not isfinite(float(rv)) or rv < 0):
                    raise ValueError(f"{prefix}.artifacts.{slot}.rv must be non-negative or null")
                normalized_artifacts[slot] = {"setKey": item["setKey"], "rv": float(rv) if rv is not None else None,
                    "level": _integer(item.get("level", 20), 0, 20, f"{prefix}.artifacts.{slot}.level"),
                    "mainStat": item.get("mainStat")}
                if rv is None:
                    warnings.append(f"{key}: {slot} RV unknown")
            active_sets = [{"setKey": set_key, "pieces": count} for set_key, count in sorted(
                Counter(item["setKey"] for item in normalized_artifacts.values()).items()) if count >= 2]
            if raw.get("activeSets") is not None and raw["activeSets"] != active_sets:
                warnings.append(f"{key}: supplied activeSets differed from equipped pieces; recalculated")
            canonical["characters"][key] = {"level": level, "ascension": ascension, "constellation": constellation,
                "weapon": weapon, "talents": normalized_talents, "artifacts": normalized_artifacts,
                "activeSets": active_sets}
            if weapon is None:
                warnings.append(f"{key}: equipped weapon missing")
            missing = set(SLOTS) - set(normalized_artifacts)
            if missing:
                warnings.append(f"{key}: artifact slots missing: {', '.join(sorted(missing))}")
        except (ValueError, TypeError) as exc:
            warnings.append(f"{key}: character skipped because its snapshot data is invalid ({exc})")
            unmapped.append(str(key))
    if problems or not canonical["characters"]:
        if not problems:
            problems.append("no valid character entries were available to import")
        raise SnapshotValidationError(problems)
    return canonical, {"charactersRead": len(data["characters"]), "charactersImported": len(canonical["characters"]),
                       "warnings": warnings, "unmapped": unmapped}


def _integer(value: Any, minimum: int, maximum: int, field: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer from {minimum} to {maximum}")
    return value
