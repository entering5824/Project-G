"""Planner policy for turning reviewed build hypotheses into safe progression targets."""

from typing import Any

from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack


def derive_profile_targets(pack: BuildKnowledgePack) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Build conservative targets from all verified hypotheses in a knowledge pack."""
    targets: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = list(pack.coverage.get("missing", []))
    for character, rows in pack.profiles.items():
        hypotheses = [row for row in rows if row.get("status") == "VERIFIED"]
        if not hypotheses:
            unresolved.append(character)
            continue
        progressions = [row["progression"] for row in hypotheses]
        talents = {}
        for name in ("normal", "skill", "burst"):
            rows_for_talent = [item["talents"][name] for item in progressions]
            enabled = all(bool(item.get("enabled", True)) for item in rows_for_talent)
            talents[name] = {
                "enabled": enabled,
                "target": min(int(item["target"]) for item in rows_for_talent) if enabled else 1,
                "importance": (
                    min(float(item.get("importance", 0.5)) for item in rows_for_talent)
                    if enabled else 0.0
                ),
            }
        targets[character] = {
            "level": min(int(item["level"]) for item in progressions),
            "ascension": min(int(item.get("ascension", 6)) for item in progressions),
            "importance": {
                "level": min(float(item.get("levelImportance", 0.7)) for item in progressions),
                "ascension": min(float(item.get("levelImportance", 0.7)) for item in progressions),
            },
            "talents": talents,
            "weapon": {
                "weaponKey": None,
                "targetLevel": min(int(item["weapon"]["targetLevel"]) for item in progressions),
                "importance": min(float(item["weapon"].get("importance", 0.7)) for item in progressions),
            },
            "artifact": {"enabled": False},
            "_buildArtifacts": [row.get("artifacts", {}) for row in hypotheses],
            "_profiles": hypotheses,
        }
    return targets, unresolved
