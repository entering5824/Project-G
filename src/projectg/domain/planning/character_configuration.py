"""Pure rules for per-character planner configuration."""

from typing import Any, Iterable


VALID_PRIORITY_OVERRIDES = frozenset({"NORMAL", "PRIORITIZED", "DEPRIORITIZED"})


def validate_character_configuration(
    *,
    owned: bool,
    tiers: Iterable[dict[str, Any]],
    tier_key: str | None,
    priority_override: str,
) -> None:
    if not owned:
        raise ValueError("Character is not owned in the current snapshot.")
    if priority_override not in VALID_PRIORITY_OVERRIDES:
        raise ValueError("Invalid priority override.")

    allowed = {item["key"] for item in tiers}
    if tier_key is not None and tier_key not in allowed:
        raise ValueError("Tier key is not configured.")
