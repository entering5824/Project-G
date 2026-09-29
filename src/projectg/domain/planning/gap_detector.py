from typing import Any
from .config import PlannerConfig
from .models import CharacterState, GoalStatus, GoalType, PlannerInput, UpgradeGoal, UnresolvedIssue
from .progress import (ascension_deficiency, character_level_deficiency,
                       next_milestone, required_ascension_for_talent,
                       talent_deficiency, weapon_level_deficiency)

TALENT_SPECS = (
    ("normal", "auto", GoalType.TALENT_AUTO),
    ("skill", "skill", GoalType.TALENT_SKILL),
    ("burst", "burst", GoalType.TALENT_BURST),
)


def _team_priority(inp: PlannerInput, character_key: str) -> tuple[float, bool, bool]:
    primary = character_key in inp.primary_team_members
    saved = character_key in inp.saved_team_members
    if primary:
        return inp.config.team_primary, saved, True
    if saved:
        return inp.config.team_saved, True, False
    return inp.config.team_none, False, False


def goal_key(character_key: str, goal_type: GoalType) -> str:
    suffix = "WEAPON" if goal_type == GoalType.WEAPON_LEVEL else goal_type.value
    return f"{character_key}:{suffix}"


def _marginal_importance(target: dict[str, Any], component: str, current: int, target_value: int,
                         base_importance: float) -> float:
    """Apply the most conservative curated per-step utility across hypotheses."""
    profiles = target.get("_profiles") or []
    field = component if component in {"normal", "skill", "burst"} else "weapon"
    factors = []
    for profile in profiles:
        progression = profile.get("progression", {})
        spec = progression.get("talents", {}).get(field, {}) if field != "weapon" else progression.get("weapon", {})
        curve = spec.get("stepUtility") or {}
        for label, value in curve.items():
            try:
                lower, upper = (int(part) for part in label.split("-", 1))
            except (ValueError, TypeError):
                continue
            if current < upper and target_value > lower:
                factors.append(float(value))
                break
    return float(base_importance) * (min(factors) if factors else 1.0)


def _combo_signature(combo) -> tuple[tuple[str, int], ...]:
    rows = []
    for item in combo or []:
        if isinstance(item, str) and ":" in item:
            key, count = item.rsplit(":", 1)
            try: rows.append((key, int(count)))
            except ValueError: pass
        elif isinstance(item, dict) and isinstance(item.get("setKey"), str):
            try: rows.append((item["setKey"], int(item.get("pieces", 4))))
            except (TypeError, ValueError): pass
    return tuple(sorted(rows))


def _artifact_build_goal(inp: PlannerInput, char: CharacterState, target: dict[str, Any],
                         unresolved: list[UnresolvedIssue]) -> UpgradeGoal | None:
    profiles = target.get("_buildArtifacts") or []
    if not profiles or any(not item for item in profiles):
        return None
    slot_thresholds = [item.get("slotRvTargets") or {} for item in profiles]
    weak_slots = []
    slot_gains = []
    for slot in ("flower", "plume", "sands", "goblet", "circlet"):
        limits = [row.get(slot, {}).get("stopFarming") for row in slot_thresholds]
        if not all(type(value) in (int, float) for value in limits):
            continue
        artifact = char.artifacts.get(slot)
        if artifact is None:
            weak_slots.append(slot)
            slot_gains.append(1.0)
            continue
        rv = artifact.get("rv")
        if rv is None:
            unresolved.append(UnresolvedIssue("ARTIFACT_RV_UNKNOWN", char.key, "info",
                "Artifact RV is unknown, so this slot is not scored as weak.", {"slot": slot}))
            continue
        if all(float(rv) < float(limit) for limit in limits):
            weak_slots.append(slot)
            slot_gains.append(min((float(limit) - float(rv)) / max(float(limit), 1.0) for limit in limits))

    current_counts: dict[str, int] = {}
    for item in char.artifacts.values():
        key = item.get("setKey")
        if key:
            current_counts[key] = current_counts.get(key, 0) + 1
    current_signature = tuple(sorted((key, count) for key, count in current_counts.items() if count >= 2))
    recommended: list[tuple[float, tuple[tuple[str, int], ...]]] = []
    for profile in profiles:
        combinations = profile.get("setCombinations") or profile.get("sets") or []
        if not combinations:
            continue
        ranked = []
        for item in combinations:
            if isinstance(item, dict):
                signature = _combo_signature(item.get("combination"))
                utility = item.get("utility")
                if signature and type(utility) in (int, float):
                    ranked.append((float(utility), signature))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        if ranked:
            recommended.append(ranked[0])
    set_gain = 0.0
    set_signature = None
    set_conflict = False
    if recommended:
        signatures = {signature for _, signature in recommended}
        if len(signatures) != 1:
            set_conflict = True
            unresolved.append(UnresolvedIssue("ARTIFACT_SET_ARCHETYPE_CONFLICT", char.key, "info",
                "Possible build profiles recommend different artifact sets; farming is deferred until the build is clearer."))
        else:
            set_signature = next(iter(signatures))
            if set_signature != current_signature:
                gains = []
                for profile in profiles:
                    combinations = profile.get("setCombinations") or profile.get("sets") or []
                    current_utility = next((float(item["utility"]) for item in combinations
                        if isinstance(item, dict) and _combo_signature(item.get("combination")) == current_signature
                        and type(item.get("utility")) in (int, float)), 0.0)
                    preferred_utility = next((utility for utility, signature in recommended
                                              if signature == set_signature), 0.0)
                    gains.append(preferred_utility - current_utility)
                set_gain = max(0.0, min(gains))
                if set_gain < 0.08:
                    set_gain = 0.0

    if set_conflict or (not weak_slots and not set_gain):
        return None
    artifact_sets = sorted({key for key, _ in (set_signature or ())})
    domains = []
    for key in artifact_sets:
        domain = inp.artifact_domains.get(key)
        if domain:
            domains.append({**domain, "setKey": key})
    known_rv = [float(char.artifacts[slot]["rv"]) for slot in weak_slots
                if char.artifacts.get(slot, {}).get("rv") is not None]
    current_score = sum(known_rv) / len(known_rv) if known_rv else 0.0
    target_score = current_score + (sum(slot_gains) / max(1, len(slot_gains)) * 100.0 if slot_gains else 0.0)
    tier_key = inp.tier_assignments.get(char.key)
    tier = inp.tiers.get(tier_key) if tier_key else None
    team_value, saved, primary = _team_priority(inp, char.key)
    return UpgradeGoal(id=f"{char.key}:ARTIFACT_QUALITY:{','.join(weak_slots)}:{','.join(artifact_sets)}",
        goal_key=goal_key(char.key, GoalType.ARTIFACT_QUALITY), character_key=char.key,
        type=GoalType.ARTIFACT_QUALITY, current_value=current_score, target_value=target_score,
        importance=0.75, deficiency=max(0.0, min(1.0, max([*slot_gains, set_gain]))),
        tier_value=tier.weight if tier else inp.config.tier_fallback, team_value=team_value,
        completion_value=0.35, priority_override=inp.config.priority_multiplier(inp.priority_overrides.get(char.key, "NORMAL")),
        summary=("Artifact set efficiency can improve." if set_gain else "Equipped artifact slot is below its profile stop-farming threshold."),
        title=f"Improve {char.key} artifacts", tier_configured=tier is not None,
        tier_key=tier.key if tier else None, tier_label=tier.label if tier else "Unranked",
        saved_team_member=saved, primary_team_member=primary,
        priority_mode=inp.priority_overrides.get(char.key, "NORMAL"), action_target=target_score,
        strategic_target=target_score, next_milestone=target_score, efficiency=0.25,
        artifact_status="BELOW_PROFILE_TARGET", artifact_quality_label=None,
        artifact_target_quality=None, artifact_target_score=target_score,
        artifact_weak_slots=weak_slots, artifact_domain_candidates=domains,
        artifact_recommended_sets=artifact_sets, artifact_candidate_class="ROBUST")


def _completion_value(state: CharacterState, target: dict[str, Any], kind: GoalType,
                      action_target: int, strategic_target: int, near_threshold: float,
                      artifact_progress: tuple[float, float] | None = None) -> float:
    components: list[tuple[str, int, int]] = [
        ("level", state.level, int(target["level"])),
        ("ascension", state.ascension, int(target["ascension"])),
    ]
    for target_name, state_name, _ in TALENT_SPECS:
        talent = target["talents"][target_name]
        if talent["enabled"]:
            components.append((state_name, state.talents[state_name], int(talent["target"])))
    if state.weapon is not None:
        components.append(("weapon", state.weapon.level, int(target["weapon"]["targetLevel"])))
    if target.get("artifact", {}).get("enabled"):
        if artifact_progress is None:
            # Unknown quality cannot grant an all-components completion bonus.
            components.append(("artifact", -1, 1))
        else:
            components.append(("artifact", artifact_progress[0], artifact_progress[1]))

    current = {name: value for name, value, _ in components}
    updated = dict(current)
    component_name = {
        GoalType.CHARACTER_LEVEL: "level",
        GoalType.CHARACTER_ASCENSION: "ascension",
        GoalType.TALENT_AUTO: "auto",
        GoalType.TALENT_SKILL: "skill",
        GoalType.TALENT_BURST: "burst",
        GoalType.WEAPON_LEVEL: "weapon",
    }[kind]
    updated[component_name] = action_target
    total = len(components)
    complete_before = sum(current[name] >= needed for name, _, needed in components)
    all_after = all(updated[name] >= needed for name, _, needed in components)
    if all_after:
        return 1.0
    if complete_before / max(total, 1) >= near_threshold:
        return 0.60
    if action_target >= strategic_target:
        return 0.35
    return 0.0


def _artifact_completion_value(inp: PlannerInput, char: CharacterState, target: dict[str, Any],
                               artifact_score: float, artifact_target_score: float) -> float:
    parts = [(char.level, target["level"]), (char.ascension, target["ascension"])]
    for target_name, state_name, _ in TALENT_SPECS:
        item = target["talents"][target_name]
        if item["enabled"]:
            parts.append((char.talents[state_name], item["target"]))
    if char.weapon:
        parts.append((char.weapon.level, target["weapon"]["targetLevel"]))
    if all(current >= needed for current, needed in parts):
        return 1.0
    parts.append((artifact_score, artifact_target_score))
    completed = sum(current >= needed for current, needed in parts)
    if all(current >= needed for current, needed in parts):
        return 1.0
    if completed / max(1, len(parts)) >= inp.config.deterministic_completion_near_threshold:
        return 0.60
    return 0.35


def _build_goal(inp: PlannerInput, char: CharacterState, target: dict[str, Any],
                kind: GoalType, current: int, action_target: int, strategic_target: int,
                importance: float, deficiency: float, dependencies: list[str] | None = None,
                blocked_by: list[str] | None = None, title: str = "", summary: str = "",
                weapon_instance_id: str | None = None, weapon_key: str | None = None,
                reported_next_milestone: int | None = None) -> UpgradeGoal:
    tier_key = inp.tier_assignments.get(char.key)
    tier = inp.tiers.get(tier_key) if tier_key else None
    configured = tier is not None
    tier_value = tier.weight if tier else inp.config.tier_fallback
    priority_mode = inp.priority_overrides.get(char.key, "NORMAL")
    team_value, saved_team_member, primary_team_member = _team_priority(inp, char.key)
    status = GoalStatus.BLOCKED if blocked_by else GoalStatus.ACTIONABLE
    artifact_progress = None
    if target.get("artifact", {}).get("enabled") and inp.artifact_quality_config is not None:
        from projectg.domain.artifacts.quality import ArtifactQualityAdapter
        evaluation = inp.artifact_evaluations.get(char.key)
        quality = ArtifactQualityAdapter().evaluate(evaluation, target["artifact"].get("targetQuality", "GOOD"),
            inp.artifact_quality_config, current_fingerprint=char.artifact_fingerprint)
        if quality.normalized_score is not None and quality.target_score is not None:
            artifact_progress = (quality.normalized_score, quality.target_score)
    return UpgradeGoal(
        id=f"{char.key}:{kind.value}:{current}:{action_target}",
        goal_key=goal_key(char.key, kind), character_key=char.key, type=kind,
        current_value=current, target_value=strategic_target, importance=float(importance),
        deficiency=deficiency, tier_value=tier_value,
        team_value=team_value,
        completion_value=_completion_value(char, target, kind, strategic_target, strategic_target,
                                           inp.config.deterministic_completion_near_threshold, artifact_progress),
        priority_override=inp.config.priority_multiplier(priority_mode),
        dependencies=list(dependencies or []), status=status,
        title=title, summary=summary, tier_configured=configured,
        priority_mode=priority_mode, weapon_instance_id=weapon_instance_id,
        weapon_key=weapon_key, action_target=action_target, strategic_target=strategic_target,
        next_milestone=reported_next_milestone if reported_next_milestone is not None else action_target,
        blocked_by=list(blocked_by or []), tier_key=tier.key if tier else None,
        tier_label=tier.label if tier else "Unranked",
        saved_team_member=saved_team_member,
        primary_team_member=primary_team_member,
    )


def detect_character_goals(inp: PlannerInput, char: CharacterState, target: dict[str, Any],
                           unresolved: list[UnresolvedIssue]) -> list[UpgradeGoal]:
    goals: list[UpgradeGoal] = []
    config = inp.config

    level_target = int(target["level"])
    if char.level < level_target:
        reported_level_milestone = next_milestone(char.level, level_target, config.level_milestones)
        current_cap = config.ascension_level_caps[char.ascension]
        level_action_target = next_milestone(char.level, level_target, config.level_milestones, current_cap)
        blocker = []
        deps = []
        if char.level >= current_cap or level_action_target <= char.level:
            if char.ascension < int(target["ascension"]):
                dependency = goal_key(char.key, GoalType.CHARACTER_ASCENSION)
                blocker.append(dependency); deps.append(dependency)
                # Preserve the strategic level gap internally while its
                # ascension prerequisite remains incomplete.
                level_action_target = level_target
            else:
                unresolved.append(UnresolvedIssue("INVALID_ACCOUNT_STATE", char.key, "warning",
                    "The current ascension cap prevents reaching this configured level target.",
                    {"currentLevel": char.level, "currentAscension": char.ascension, "targetLevel": level_target}))
        if level_action_target > char.level:
            goals.append(_build_goal(inp, char, target, GoalType.CHARACTER_LEVEL, char.level,
                level_action_target, level_target, target["importance"]["level"],
                character_level_deficiency(char.level, level_target, config), deps, blocker,
                f"Raise {char.key} to Lv. {level_target}",
                f"Character level is below the configured target of Lv. {level_target}.",
                reported_next_milestone=reported_level_milestone))

    ascension_target = int(target["ascension"])
    if char.ascension < ascension_target:
        action_target = char.ascension + 1
        current_cap = config.ascension_level_caps[char.ascension]
        blocked_by = []
        deps = []
        if char.level < current_cap:
            dependency = goal_key(char.key, GoalType.CHARACTER_LEVEL)
            blocked_by.append(dependency); deps.append(dependency)
        goals.append(_build_goal(inp, char, target, GoalType.CHARACTER_ASCENSION,
            char.ascension, action_target, ascension_target, target["importance"]["ascension"],
            ascension_deficiency(char.ascension, ascension_target), deps, blocked_by,
            f"Ascend {char.key} to phase {ascension_target}",
            f"Character ascension is below the configured target of phase {ascension_target}."))

    for target_name, state_name, kind in TALENT_SPECS:
        talent = target["talents"][target_name]
        if not talent["enabled"]:
            continue
        current = char.talents[state_name]
        talent_target = int(talent["target"])
        if talent_target > 10:
            # GOOD's talent fields are base/invested talent ranks and exclude
            # the C3/C5 +3 bonuses. Which talent receives the bonus is
            # character-specific, so do not guess or emit an impossible action.
            unresolved.append(UnresolvedIssue("TALENT_TARGET_CONSTELLATION_NORMALIZATION_REQUIRED",
                char.key, "warning", "Target exceeds the GOOD base talent range; character-specific constellation bonus mapping is not available.",
                {"talent": target_name, "target": talent_target, "goodTalentValuesAreBase": True}))
            continue
        if current >= talent_target:
            continue
        required_ascension = required_ascension_for_talent(talent_target, config)
        if int(target["ascension"]) < required_ascension:
            unresolved.append(UnresolvedIssue("IMPOSSIBLE_TALENT_TARGET_ASCENSION", char.key, "warning",
                "The configured ascension target cannot unlock the requested talent investment rank.",
                {"talent":target_name,"talentTarget":talent_target,"minimumAscension":required_ascension,
                 "configuredAscension":int(target["ascension"])}))
        blocked_by = []
        deps = []
        if char.ascension < required_ascension:
            dependency = goal_key(char.key, GoalType.CHARACTER_ASCENSION)
            blocked_by.append(dependency); deps.append(dependency)
        talent_goal = _build_goal(inp, char, target, kind, current, min(current + 1, talent_target),
            talent_target, _marginal_importance(target, target_name, current,
                min(current + 1, talent_target), talent["importance"]), talent_deficiency(current, talent_target),
            deps, blocked_by, f"Upgrade {char.key} {target_name.title()} {current} → {talent_target}",
            f"{target_name.title()} talent is below its configured target.")
        talent_goal.next_milestone = min(current + 1, talent_target)
        goals.append(talent_goal)

    weapon_target = int(target["weapon"]["targetLevel"])
    target_weapon_key = target["weapon"].get("weaponKey")
    if char.weapon is None:
        if weapon_target > 1 or target_weapon_key:
            unresolved.append(UnresolvedIssue("EQUIPPED_WEAPON_MISSING", char.key, "warning",
                "No currently equipped weapon is present in this GOOD snapshot.",
                {"targetLevel": weapon_target, "targetWeaponKey": target_weapon_key}))
    elif target_weapon_key and char.weapon.key != target_weapon_key:
        unresolved.append(UnresolvedIssue("WEAPON_TARGET_MISMATCH", char.key, "warning",
            "The equipped weapon does not match the specifically configured weapon target.",
            {"currentWeaponKey": char.weapon.key, "targetWeaponKey": target_weapon_key,
             "currentLevel": char.weapon.level, "targetLevel": weapon_target}))
    elif char.weapon.level < weapon_target:
        weapon_next_milestone = next_milestone(char.weapon.level, weapon_target, config.weapon_milestones)
        goals.append(_build_goal(inp, char, target, GoalType.WEAPON_LEVEL,
            char.weapon.level, weapon_next_milestone, weapon_target,
            _marginal_importance(target, "weapon", char.weapon.level, weapon_next_milestone,
                                 target["weapon"]["importance"]),
            weapon_level_deficiency(char.weapon.level, weapon_target, config),
            title=f"Upgrade {char.weapon.key}",
            summary="Equipped weapon is below its configured target level.",
            weapon_instance_id=char.weapon.instance_id, weapon_key=char.weapon.key,
            ))
        goals[-1].weapon_ascension = char.weapon.ascension

    artifact_target = target.get("artifact", {})
    if artifact_target.get("enabled"):
        from projectg.domain.artifacts.quality import ArtifactQualityAdapter
        quality_config = inp.artifact_quality_config
        if quality_config is None:
            unresolved.append(UnresolvedIssue("ARTIFACT_QUALITY_CONFIG_MISSING", char.key, "warning",
                "Configure artifact quality thresholds before artifact progress can be scored."))
        else:
            evaluation = inp.artifact_evaluations.get(char.key)
            result = ArtifactQualityAdapter().evaluate(evaluation, artifact_target.get("targetQuality", "GOOD"),
                quality_config, current_fingerprint=char.artifact_fingerprint)
            if result.status.value == "UNKNOWN":
                unresolved.append(UnresolvedIssue("ARTIFACT_DATA_MISSING", char.key, "warning",
                    "Artifact target is enabled, but no confirmed manual evaluation exists."))
            elif result.status.value == "NEEDS_QUALITY_CONFIG":
                unresolved.append(UnresolvedIssue("ARTIFACT_QUALITY_CONFIG_MISSING", char.key, "warning",
                    result.message or "Artifact quality thresholds are not configured."))
            elif result.status.value == "INVALID_DATA":
                unresolved.append(UnresolvedIssue("ARTIFACT_EVALUATION_INVALID", char.key, "warning",
                    result.message or "Artifact evaluation could not be interpreted."))
            else:
                if result.stale:
                    unresolved.append(UnresolvedIssue("ARTIFACT_DATA_STALE", char.key, "warning",
                        "The equipped artifact fingerprint differs from the evaluation; the confirmed evaluation is still used.",
                        {"evaluationId": evaluation.get("id")}))
                gate = artifact_target.get("gate") or {}
                gate_failures = []
                if gate.get("minLevel") is not None and char.level < int(gate["minLevel"]):
                    gate_failures.append("ARTIFACT_GATE_LEVEL")
                if gate.get("minAscension") is not None and char.ascension < int(gate["minAscension"]):
                    gate_failures.append("ARTIFACT_GATE_ASCENSION")
                if gate.get("weaponMinLevel") is not None and (char.weapon is None or char.weapon.level < int(gate["weaponMinLevel"])):
                    gate_failures.append("ARTIFACT_GATE_WEAPON")
                for talent_name in gate.get("requiredTalents", []):
                    target_key = str(talent_name).lower().replace("talent_", "")
                    state_key = {"normal": "auto"}.get(target_key, target_key)
                    talent_target = target.get("talents", {}).get(target_key)
                    if (not talent_target or not talent_target.get("enabled")
                            or char.talents.get(state_key, 0) < int(talent_target.get("target", 1))):
                        gate_failures.append("ARTIFACT_GATE_TALENT")
                        break
                if gate_failures:
                    unresolved.append(UnresolvedIssue("ARTIFACT_GATE_BLOCKED", char.key, "info",
                        "Artifact progression is gated until the configured character requirements are met.",
                        {"reasons": gate_failures, "gate": gate}))
                if result.status.value == "BELOW_TARGET" or gate_failures:
                    tier_key = inp.tier_assignments.get(char.key)
                    tier = inp.tiers.get(tier_key) if tier_key else None
                    priority_mode = inp.priority_overrides.get(char.key, "NORMAL")
                    team_value, saved_team_member, primary_team_member = _team_priority(inp, char.key)
                    reason_codes = ["ARTIFACT_BELOW_TARGET"] if result.status.value == "BELOW_TARGET" else ["ARTIFACT_GATE_BLOCKED"]
                    if result.deficiency is not None and result.deficiency >= 0.5:
                        reason_codes.append("ARTIFACT_FAR_BELOW_TARGET")
                    if artifact_target.get("importance", 0) >= 0.8:
                        reason_codes.append("ARTIFACT_HIGH_IMPORTANCE")
                    if result.stale:
                        reason_codes.append("ARTIFACT_DATA_STALE")
                    candidate_domains = []
                    for set_key in [*(artifact_target.get("primarySets") or []), *(artifact_target.get("alternativeSets") or [])]:
                        mapping = inp.artifact_domains.get(set_key)
                        if mapping and mapping not in candidate_domains:
                            candidate_domains.append({**mapping, "setKey": set_key})
                    blocked = bool(gate_failures)
                    goal = UpgradeGoal(
                        id=f"{char.key}:ARTIFACT_QUALITY:{evaluation.get('id') if evaluation else 'unknown'}",
                        goal_key=goal_key(char.key, GoalType.ARTIFACT_QUALITY), character_key=char.key,
                        type=GoalType.ARTIFACT_QUALITY, current_value=result.normalized_score,
                        target_value=artifact_target.get("targetQuality", "GOOD"),
                        importance=float(artifact_target.get("importance", 0)),
                        deficiency=float(result.deficiency or 0), tier_value=tier.weight if tier else inp.config.tier_fallback,
                        team_value=team_value,
                        completion_value=_artifact_completion_value(inp, char, target, result.normalized_score or 0,
                            result.target_score or 1), priority_override=inp.config.priority_multiplier(priority_mode),
                        dependencies=[], status=GoalStatus.BLOCKED if blocked else GoalStatus.ACTIONABLE,
                        reason_codes=reason_codes, summary=(result.message or "Artifact quality is below the configured target."),
                        title=f"Improve {char.key} artifact quality", tier_configured=tier is not None,
                        tier_key=tier.key if tier else None, tier_label=tier.label if tier else "Unranked",
                        saved_team_member=saved_team_member, primary_team_member=primary_team_member,
                        priority_mode=priority_mode,
                        action_target=result.target_score, strategic_target=result.target_score,
                        next_milestone=result.target_score, blocked_by=gate_failures,
                        efficiency=0.40, artifact_status=result.status.value,
                        artifact_quality_label=result.quality_label, artifact_target_quality=artifact_target.get("targetQuality"),
                        artifact_target_score=result.target_score, artifact_weak_slots=result.weak_slots,
                        artifact_stale=result.stale, artifact_developer_input=result.developer_input,
                        artifact_domain_candidates=candidate_domains)
                    goals.append(goal)
                elif result.status.value == "COMPLETE":
                    unresolved.append(UnresolvedIssue("ARTIFACT_TARGET_REACHED", char.key, "info",
                        "The latest confirmed artifact evaluation meets the target."))
    artifact_goal = _artifact_build_goal(inp, char, target, unresolved)
    if artifact_goal is not None:
        goals.append(artifact_goal)
    return goals


def detect_goals(inp: PlannerInput) -> tuple[list[UpgradeGoal], list[UnresolvedIssue]]:
    goals: list[UpgradeGoal] = []
    unresolved: list[UnresolvedIssue] = []
    missing_targets: list[str] = []
    missing_tiers: list[str] = []
    for key, char in sorted(inp.characters.items()):
        target = inp.character_targets.get(key)
        if target is None:
            missing_targets.append(key)
        else:
            goals.extend(detect_character_goals(inp, char, target, unresolved))
        if inp.tier_assignments.get(key) not in inp.tiers:
            missing_tiers.append(key)
    if missing_targets:
        unresolved.append(UnresolvedIssue("TARGET_NOT_CONFIGURED", None, "info",
            f"{len(missing_targets)} nhân vật chưa có target — chúng sẽ không tham gia strategic plan.",
            {"count": len(missing_targets), "characterKeys": missing_targets, "group": "MISSING_TARGET"}))
    if missing_tiers:
        unresolved.append(UnresolvedIssue("TIER_NOT_CONFIGURED", None, "info",
            f"{len(missing_tiers)} nhân vật chưa được xếp tier.",
            {"count": len(missing_tiers), "characterKeys": missing_tiers,
             "group": "UNRANKED", "manualPriorityCanInclude": True}))
    return goals, unresolved
