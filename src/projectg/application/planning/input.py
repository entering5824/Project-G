"""Compose normalized planner-domain input from persisted facts and external catalogs."""

from dataclasses import dataclass
from typing import Any

from projectg.application.planning.build_knowledge import derive_profile_targets
from projectg.application.planning.readiness import assess_build_readiness
from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack
from projectg.application.ports.outbound.planner_gateway import PlannerFacts
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.config import PlannerConfig
from projectg.domain.planning.models import CharacterState, PlannerInput, TierValue, WeaponState
from projectg.domain.planning.tiers import ELIGIBLE_MINIMUMS, label_for


@dataclass(frozen=True)
class PreparedPlannerInput:
    value: PlannerInput
    issues: tuple[dict[str, Any], ...]


def prepare_planner_input(
    facts: PlannerFacts,
    game: GameData,
    build_pack: BuildKnowledgePack | None,
    config: PlannerConfig,
) -> PreparedPlannerInput:
    artifact_domains = {
        key: {"key": domain.key, "name": domain.name or domain.key}
        for key, definition in game.artifact_sets.items()
        if (domain := game.domains.get(definition.domain_key))
    }
    if not facts.has_snapshot:
        return PreparedPlannerInput(
            PlannerInput(
                {}, {}, {}, {}, {}, set(), config,
                artifact_quality_config=facts.artifact_quality_config,
                artifact_domains=artifact_domains,
            ),
            ({
                "code": "INVALID_ACCOUNT_STATE",
                "characterKey": None,
                "severity": "warning",
                "message": "No GOOD account snapshot is available.",
                "details": {},
            },),
        )

    characters = {
        fact.key: CharacterState(
            key=fact.key,
            level=fact.level,
            ascension=fact.ascension,
            talents=dict(fact.talents),
            weapon=(
                WeaponState(
                    fact.weapon.instance_id,
                    fact.weapon.key,
                    fact.weapon.level,
                    fact.weapon.ascension,
                )
                if fact.weapon else None
            ),
            artifact_fingerprint=fact.artifact_fingerprint,
            constellation=fact.constellation,
            artifacts={slot: {
                "setKey": item.set_key, "rv": item.rv, "rvStatus": item.rv_status,
                "level": item.level, "mainStat": item.main_stat,
            } for slot, item in fact.artifacts.items()},
        )
        for fact in facts.characters
    }

    if build_pack is None:
        derived_targets: dict[str, dict[str, Any]] = {}
        unresolved_profiles = sorted(characters)
        pack_version = "unknown"
        build_errors: tuple[str, ...] = ("Build knowledge pack is unavailable.",)
        coverage: dict[str, Any] = {"recommendationsReady": False}
    else:
        derived_targets, unresolved_profiles = derive_profile_targets(build_pack)
        pack_version = build_pack.version
        build_errors = build_pack.errors
        coverage = build_pack.coverage

    targets = (
        derived_targets
        if coverage.get("recommendationsReady") and not build_errors
        else {}
    )

    tier_scores = dict(facts.tier_pack.scores)
    tiers = {
        f"score:{score}": TierValue(f"score:{score}", label_for(score), score / 100.0)
        for score in set(tier_scores.values())
    }
    assignments = {key: f"score:{score}" for key, score in tier_scores.items()}

    artifact_evaluations: dict[str, dict[str, Any]] = {}
    for row in facts.artifact_evaluations:
        if row.character_key not in characters or row.character_key in artifact_evaluations:
            continue
        current_fingerprint = characters[row.character_key].artifact_fingerprint
        stale = bool(
            row.artifact_fingerprint
            and row.artifact_fingerprint != current_fingerprint
        )
        freshness = (
            "POSSIBLY_STALE"
            if stale
            else (
                "CURRENT"
                if row.artifact_fingerprint and current_fingerprint
                else "UNKNOWN"
            )
        )
        artifact_evaluations[row.character_key] = {
            "id": row.id,
            "characterKey": row.character_key,
            "importedAt": row.imported_at.isoformat(),
            "source": row.source,
            "status": row.status,
            "rawMetrics": row.raw_metrics,
            "normalizedMetrics": row.normalized_metrics,
            "parserConfidence": row.parser_confidence,
            "artifactFingerprint": row.artifact_fingerprint,
            "stale": stale,
            "freshnessStatus": freshness,
        }

    minimum_key = facts.tier_pack.minimum_tier_for_roadmap
    minimum_score = ELIGIBLE_MINIMUMS.get(minimum_key, ELIGIBLE_MINIMUMS["B"])
    theater = facts.theater_config
    elements = set(theater.get("elements", []))
    excluded = set(theater.get("excludedCharacters", []))
    selected = set(theater.get("selectedCharacters", []))
    manual_selection = bool(theater.get("manualSelection", bool(selected)))
    candidates = [key for key in characters if key in game.characters
                  and game.characters[key].element in elements and key not in excluded]
    if manual_selection:
        candidates = [key for key in candidates if key in selected]
    rv_threshold = None
    quality = facts.artifact_quality_config
    if quality is not None and quality.adapter_type == "rv":
        good_threshold = (quality.thresholds or {}).get("GOOD")
        rv_threshold = float(good_threshold) if good_threshold is not None else None
    readiness = {key: assess_build_readiness(characters[key], targets.get(key),
                  rv_threshold=rv_threshold) for key in candidates}
    candidates.sort(key=lambda key: (
        0 if readiness[key]["status"] == "READY" else 1,
        -(tier_scores.get(key, 0)), -float(facts.priority_overrides.get(key) == "PRIORITIZED"), key))
    theater_keys = set(candidates[:int(theater.get("requiredCharacters", 0))])
    planner_input = PlannerInput(
        characters,
        targets,
        tiers,
        assignments,
        dict(facts.priority_overrides),
        {member for team in facts.teams for member in team.members},
        config,
        primary_team_members={member for team in facts.teams if team.is_primary for member in team.members},
        artifact_evaluations=artifact_evaluations,
        artifact_quality_config=facts.artifact_quality_config,
        artifact_domains=artifact_domains,
        include_unranked_in_plan=False,
        tier_scores=tier_scores,
        planner_controls=dict(facts.tier_pack.controls),
        minimum_tier_score=minimum_score,
        selected_sets=dict(facts.tier_pack.selected_sets),
        personal_priority_keys=set(facts.personal_priority_keys),
        theater_priority_keys=theater_keys,
        theater_readiness=readiness,
        theater_candidate_keys=list(candidates),
        theater_required_characters=int(theater.get("requiredCharacters", 0)),
    )

    issues: list[dict[str, Any]] = [
        {
            "code": "BUILD_PROFILE_MISSING",
            "characterKey": key,
            "severity": "warning",
            "message": "No verified default build profile is available for this character.",
            "details": {"group": "BUILD_KNOWLEDGE", "packVersion": pack_version},
        }
        for key in sorted(unresolved_profiles)
    ]
    if build_errors:
        issues.append({
            "code": "BUILD_PACK_INVALID",
            "characterKey": None,
            "severity": "error",
            "message": "Build knowledge pack failed validation.",
            "details": {"errors": list(build_errors)},
        })
    if coverage.get("recommendationsReady") and not coverage.get("advancedCoverageReady"):
        issues.append({
            "code": "BUILD_KNOWLEDGE_DEPTH",
            "characterKey": None,
            "severity": "info",
            "message": (
                "Account roadmap is using the complete Basic profiles; "
                "Standard/Deep profile coverage is still being expanded."
            ),
            "details": coverage,
        })
    if not coverage.get("recommendationsReady"):
        issues.append({
            "code": "BUILD_KNOWLEDGE_COVERAGE",
            "characterKey": None,
            "severity": "warning",
            "message": (
                "Full-roster Basic profile coverage is incomplete; "
                "account-wide recommendations are withheld."
            ),
            "details": coverage,
        })
    return PreparedPlannerInput(planner_input, tuple(issues))
