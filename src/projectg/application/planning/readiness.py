"""Conservative per-character readiness against verified build profiles."""

from typing import Any


def assess_build_readiness(character: Any, targets: dict | None, *, rv_threshold: float | None = None) -> dict:
    if not targets or not targets.get("_profiles"):
        return {"status": "UNKNOWN", "missing": ["Thiếu Build Knowledge đã xác minh"]}
    missing: list[str] = []
    if character.level < int(targets["level"]):
        missing.append(f"Nhân vật Lv {character.level}/{targets['level']}")
    target_ascension = int(targets.get("ascension", 0))
    if getattr(character, "ascension", 0) < target_ascension:
        missing.append(f"Đột phá {getattr(character, 'ascension', 0)}/{target_ascension}")
    if character.weapon is None:
        missing.append("Chưa trang bị vũ khí")
    elif character.weapon.level < int(targets["weapon"]["targetLevel"]):
        missing.append(f"Vũ khí Lv {character.weapon.level}/{targets['weapon']['targetLevel']}")
    talent_names = {"normal": "auto", "skill": "skill", "burst": "burst"}
    for name, spec in targets["talents"].items():
        if spec.get("enabled") and character.talents.get(talent_names[name], 1) < int(spec["target"]):
            missing.append(f"Thiên phú {name}: {character.talents.get(talent_names[name], 1)}/{spec['target']}")
    profiles = targets.get("_buildArtifacts") or []
    if not profiles:
        return {"status": "UNKNOWN", "missing": [*missing, "Thiếu tiêu chuẩn thánh di vật"]}
    build_profiles = targets.get("_profiles") or []
    signatures = {repr(profile.get("setCombinations") or profile.get("sets") or [])
                  for profile in build_profiles}
    if len(signatures) > 1:
        return {"status": "UNKNOWN", "missing": [*missing, "Build profile chưa thống nhất bộ thánh di vật"]}
    combinations_by_profile = [profile.get("setCombinations") or profile.get("sets") or []
                               for profile in build_profiles]
    if not combinations_by_profile or any(not items for items in combinations_by_profile):
        return {"status": "UNKNOWN", "missing": [*missing, "Thiếu tổ hợp bộ thánh di vật đã xác minh"]}
    current_counts: dict[str, int] = {}
    for artifact in character.artifacts.values():
        set_key = artifact.get("setKey")
        if set_key:
            current_counts[set_key] = current_counts.get(set_key, 0) + 1
    matches = False
    for combinations in combinations_by_profile:
        profile_matches = False
        for choice in combinations:
            raw = choice.get("combination", []) if isinstance(choice, dict) else []
            required: dict[str, int] = {}
            for entry in raw:
                if isinstance(entry, str) and ":" in entry:
                    key, pieces = entry.rsplit(":", 1)
                    if pieces.isdigit():
                        required[key] = int(pieces)
                elif isinstance(entry, dict) and isinstance(entry.get("setKey"), str):
                    required[entry["setKey"]] = int(entry.get("pieces", 4))
            if required and all(current_counts.get(key, 0) >= pieces for key, pieces in required.items()):
                profile_matches = True
                break
        matches = matches or profile_matches
        if not profile_matches:
            matches = False
            break
    if not matches:
        missing.append("Bộ thánh di vật chưa khớp build đã xác minh")
    limits = [profile.get("slotRvTargets") or {} for profile in profiles]
    for slot in ("flower", "plume", "sands", "goblet", "circlet"):
        thresholds = [row.get(slot, {}).get("stopFarming") for row in limits]
        threshold = (max(float(value) for value in thresholds)
                     if thresholds and all(type(value) in (int, float) for value in thresholds)
                     else rv_threshold)
        if threshold is None:
            return {"status": "UNKNOWN", "missing": [*missing, f"Cần cấu hình ngưỡng RV GOOD: {slot}"]}
        artifact = character.artifacts.get(slot)
        if artifact is None:
            missing.append(f"Chưa có thánh di vật: {slot}")
        elif artifact.get("rv") is None:
            missing.append(f"Cần điền RV: {slot}")
        elif float(artifact["rv"]) < threshold:
            missing.append(f"RV chưa đạt: {slot}")
    if any("Cần điền RV" in item for item in missing):
        status = "NEEDS_RV"
    elif missing:
        status = "IN_PROGRESS"
    else:
        status = "READY"
    return {"status": status, "missing": missing}
