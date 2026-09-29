"""Pure validation and normalization for user-configured planner teams."""

import re
from typing import Any, Iterable


def normalize_configured_teams(
    rows: list[dict[str, Any]],
    *,
    owned_characters: Iterable[str],
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("Teams must be a list.")

    owned = set(owned_characters)
    checked: list[dict[str, Any]] = []
    seen: set[str] = set()
    primary_count = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Team row {index + 1} is invalid.")

        name = str(row.get("name") or "").strip()
        members = row.get("members")
        if not name:
            raise ValueError(f"Team row {index + 1} needs a name.")
        if not isinstance(members, list) or not 1 <= len(members) <= 4:
            raise ValueError(f"Team {name} must contain 1 to 4 characters.")

        is_primary = bool(row.get("isPrimary", False))
        if is_primary:
            primary_count += 1
            if primary_count > 1:
                raise ValueError("Only one configured planner team can be the primary team.")

        normalized_members = [str(key).strip() for key in members]
        if len(set(normalized_members)) != len(normalized_members):
            raise ValueError(f"Team {name} contains a duplicate character.")
        unknown = sorted(set(normalized_members) - owned)
        if unknown:
            raise ValueError(f"Team {name} contains unowned characters: {', '.join(unknown)}.")

        key = str(row.get("teamId") or "").strip()
        if not key:
            key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or f"team-{index + 1}"
        base = key
        suffix = 2
        while key in seen:
            key = f"{base[:42]}-{suffix}"
            suffix += 1
        seen.add(key)

        checked.append({
            "teamId": key,
            "name": name,
            "members": normalized_members,
            "isPrimary": is_primary,
        })

    return checked
