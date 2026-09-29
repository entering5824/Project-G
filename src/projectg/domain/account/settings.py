"""Pure normalization rules for account-level planner settings."""

from typing import Any


SUPPORTED_SERVER_REGIONS = frozenset({"ASIA", "EUROPE", "AMERICA", "TW_HK_MO"})


def normalize_account_settings(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Account settings must be an object.")

    region = str(payload.get("serverRegion") or "").upper()
    if region not in SUPPORTED_SERVER_REGIONS:
        raise ValueError("Unsupported server region.")

    language = str(payload.get("gameLanguage") or "").strip()
    world = payload.get("worldLevel")
    resin = payload.get("resin")
    if not language:
        raise ValueError("Game language cannot be blank.")
    if isinstance(world, bool) or not isinstance(world, int) or not 0 <= world <= 9:
        raise ValueError("World Level must be between 0 and 9.")
    if resin is not None and (
        isinstance(resin, bool) or not isinstance(resin, int) or not 0 <= resin <= 200
    ):
        raise ValueError("Resin must be unknown or between 0 and 200.")

    weekly = sorted({
        str(value).strip()
        for value in payload.get("weeklyClaimed", [])
        if str(value).strip()
    })
    unavailable = sorted({
        str(value).strip()
        for value in payload.get("unavailableSources", [])
        if str(value).strip()
    })

    return {
        "serverRegion": region,
        "gameLanguage": language,
        "worldLevel": world,
        "resin": resin,
        "weeklyClaimed": weekly,
        "unavailableSources": unavailable,
    }
