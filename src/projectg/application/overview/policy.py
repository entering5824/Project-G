"""Pure application projection for the desktop overview."""

from projectg.application.ports.outbound.overview_gateway import OverviewContext, OverviewData
from projectg.domain.planning.tiers import label_for


def build_overview(context: OverviewContext) -> OverviewData:
    if context.snapshot_id is None:
        return OverviewData({
            "snapshotId": None,
            "today": None,
            "roadmap": None,
            "characters": [],
        })

    characters = []
    for row in context.characters:
        characters.append({
            "key": row.key,
            "level": row.level,
            "ascension": row.ascension,
            "constellation": row.constellation,
            "talents": dict(row.talents),
            "weapon": dict(row.weapon) if row.weapon is not None else None,
            "artifacts": [dict(item) for item in row.artifacts],
            "target": None,
            "targetVersion": None,
            "artifactStatus": {},
            "completion": None,
            "activePresetKey": "automatic",
            "presets": [],
            "tier": label_for(row.tier_score),
            "tierScore": row.tier_score,
            "priorityOverride": row.priority_override,
            "element": row.element,
            "buildProfiles": [dict(item) for item in row.build_profiles],
            "knowledgeCoverage": dict(row.knowledge_coverage),
            "teams": [dict(item) for item in row.teams],
        })

    return OverviewData({
        "snapshotId": context.snapshot_id,
        "snapshotImportedAt": context.snapshot_imported_at.isoformat() if context.snapshot_imported_at else None,
        "today": context.today,
        "roadmap": context.roadmap,
        "characters": characters,
        "personalPriorities": dict(context.personal_priorities or {}),
        "theaterPreparation": dict(context.theater_config or {}),
    })
