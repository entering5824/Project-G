"""Pure rules for manually-authored planner tier score packs."""

from typing import Any

from projectg.domain.planning.tiers import ELIGIBLE_MINIMUMS


def blank_tier_pack() -> dict[str, Any]:
    return {
        "version": 1,
        "ratings": {},
        "minimumTierForRoadmap": "B",
        "controls": {},
        "selectedSets": {},
    }


def validate_tier_pack(
    value: dict[str, Any],
    *,
    known_keys: set[str],
    known_sets: set[str],
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("TierPack version must be 1")

    ratings = value.get("ratings")
    if not isinstance(ratings, dict):
        raise ValueError("TierPack ratings must be an object")

    normalized: dict[str, dict[str, Any]] = {}
    for key, rating in ratings.items():
        if key not in known_keys:
            raise ValueError(f"Unknown character key: {key}")
        if not isinstance(rating, dict):
            raise ValueError(f"{key}: rating must be an object")
        score = rating.get("score")
        if score is not None and (type(score) is not int or not 0 <= score <= 100):
            raise ValueError(f"{key}: score must be an integer from 0 to 100 or null")
        note = rating.get("notes", "")
        if not isinstance(note, str):
            raise ValueError(f"{key}: notes must be text")
        normalized[key] = {"score": score, "notes": note.strip()}

    minimum = value.get("minimumTierForRoadmap", "B")
    if minimum not in ELIGIBLE_MINIMUMS:
        raise ValueError("Invalid minimumTierForRoadmap")

    controls = value.get("controls", {})
    if not isinstance(controls, dict) or any(
        key not in known_keys or mode not in {"FORCE_INCLUDE", "IGNORE"}
        for key, mode in controls.items()
    ):
        raise ValueError("Invalid planner controls")

    selected_sets = value.get("selectedSets", {})
    if not isinstance(selected_sets, dict) or any(
        key not in known_keys or set_key not in known_sets
        for key, set_key in selected_sets.items()
    ):
        raise ValueError("Invalid selectedSets")

    return {
        "version": 1,
        "ratings": normalized,
        "minimumTierForRoadmap": minimum,
        "controls": dict(controls),
        "selectedSets": dict(selected_sets),
    }


def tier_pack_content(pack: dict[str, Any]) -> dict[str, Any]:
    """Return only user-authored fields, excluding persistence metadata."""
    return {
        key: pack.get(key)
        for key in ("version", "ratings", "minimumTierForRoadmap", "controls", "selectedSets")
    }
