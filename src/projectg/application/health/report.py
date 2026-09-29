from collections.abc import Iterable

from projectg.domain.planning.models import PlannerResult


DECISION_IMPACT = {
    "MISSING_TARGET": "Nhân vật chưa có target không được đưa vào roadmap nâng cấp.",
    "MISSING_TIER": "Planner dùng tier fallback; thứ tự ưu tiên có thể khác ý định của bạn.",
    "MISSING_ARTIFACT_EVALUATION": "Roadmap chưa thể xếp hạng mục tiêu artifact theo chất lượng hiện tại.",
    "MISSING_ARTIFACT_QUALITY_CONFIG": "Không thể đánh giá artifact theo tiêu chí account cho đến khi cấu hình quality.",
    "GAME_DATA_MISSING": "Planner không thể tính đầy đủ cost hoặc mục tiêu cho dữ liệu game liên quan.",
    "COST_DATA_MISSING": "Tổng nguyên liệu cần cho roadmap chưa đầy đủ.",
    "SOURCE_MAPPING_MISSING": "Có mục tiêu nhưng planner chưa xác định được nơi farm đáng tin cậy.",
    "STALE_ARTIFACT_EVALUATION": "Đánh giá artifact không còn khớp loadout; artifact có thể bị xếp sai trạng thái.",
    "GAME_DATA_CHARACTER_COVERAGE": "Nhân vật trong account chưa có dữ liệu game; cost/progression có thể thiếu.",
    "GAME_DATA_WEAPON_COVERAGE": "Vũ khí đang trang bị chưa có dữ liệu game; cost/progression có thể thiếu.",
    "BACKEND_ERROR": "Kết quả planner/Data Health hiện không đáng tin cho đến khi lỗi được xử lý.",
}


def build_data_health_report(
    *,
    planner_result: PlannerResult | None,
    artifact_quality_configured: bool,
    game_error: dict | str | None,
    plan_cost: dict | None,
    missing_character_keys: Iterable[str] = (),
    missing_weapon_keys: Iterable[str] = (),
    backend_errors: Iterable[str] = (),
    account_available: bool = True,
) -> dict:
    """Turn collected runtime facts into the product's data-health decision contract.

    Persistence adapters collect facts. This application policy decides which
    issues exist, their severity, and how they affect planner decisions.
    """
    issues: list[dict] = []

    def add(code: str, severity: str, count: int, action: str, details=None) -> None:
        if count:
            issues.append(
                {
                    "code": code,
                    "severity": severity,
                    "count": count,
                    "action": action,
                    "details": details or {},
                }
            )

    if planner_result is not None:
        missing_targets = sum(
            int((item.details or {}).get("count", 1))
            for item in planner_result.unresolved
            if item.code == "TARGET_NOT_CONFIGURED"
        )
        missing_tiers = sum(
            int((item.details or {}).get("count", 1))
            for item in planner_result.unresolved
            if item.code == "TIER_NOT_CONFIGURED"
        )
        add("MISSING_TARGET", "WARNING", missing_targets, "CONFIGURE_TARGETS")
        add("MISSING_TIER", "WARNING", missing_tiers, "ASSIGN_TIERS")
        add(
            "MISSING_ARTIFACT_EVALUATION",
            "WARNING",
            planner_result.artifact_enabled_characters
            - planner_result.artifact_evaluated_characters,
            "UPDATE_ARTIFACT_DATA",
        )
        if planner_result.artifact_enabled_characters and not artifact_quality_configured:
            add(
                "MISSING_ARTIFACT_QUALITY_CONFIG",
                "WARNING",
                1,
                "CONFIGURE_ARTIFACT_QUALITY",
            )

        codes = {item.code for item in planner_result.unresolved}
        missing_game = sorted(
            {
                item.character_key
                for item in planner_result.unresolved
                if item.code in {"GAME_DATA_MISSING", "INVALID_ACCOUNT_STATE"}
                and item.character_key
            }
        )
        add(
            "GAME_DATA_MISSING",
            "ERROR" if game_error else "WARNING",
            max(len(missing_game), 1 if game_error else 0),
            "REVIEW_GAME_DATA",
            {"characters": missing_game, "error": game_error},
        )

        cost_unresolved = (plan_cost or {}).get("unresolved", [])
        add(
            "COST_DATA_MISSING",
            "WARNING",
            sum(1 for item in cost_unresolved if item.get("code") == "COST_DATA_MISSING"),
            "REVIEW_GAME_DATA",
        )

        source_codes = {
            "ARTIFACT_DOMAIN_MISSING",
            "TASK_SOURCE_UNRESOLVED",
            "SOURCE_MAPPING_MISSING",
        }
        add(
            "SOURCE_MAPPING_MISSING",
            "WARNING",
            sum(1 for item in planner_result.unresolved if item.code in source_codes),
            "CONFIGURE_SOURCES",
            {"codes": sorted(source_codes & codes)},
        )
        add(
            "STALE_ARTIFACT_EVALUATION",
            "INFO",
            sum(
                1
                for item in planner_result.unresolved
                if item.code == "ARTIFACT_DATA_STALE"
            ),
            "REVIEW_ARTIFACT_DATA",
        )

        unresolved_by_code: dict[str, dict[str, list[str]]] = {}
        for item in planner_result.unresolved:
            group = unresolved_by_code.setdefault(
                item.code, {"characters": [], "messages": []}
            )
            if item.character_key:
                group["characters"].append(item.character_key)
            group["characters"].extend((item.details or {}).get("characterKeys", []))
            if item.message:
                group["messages"].append(item.message)

        source_map = {
            "MISSING_TARGET": ("TARGET_NOT_CONFIGURED",),
            "MISSING_TIER": ("TIER_NOT_CONFIGURED",),
            "MISSING_ARTIFACT_EVALUATION": ("ARTIFACT_DATA_MISSING",),
            "STALE_ARTIFACT_EVALUATION": ("ARTIFACT_DATA_STALE",),
            "SOURCE_MAPPING_MISSING": (
                "ARTIFACT_DOMAIN_MISSING",
                "TASK_SOURCE_UNRESOLVED",
                "SOURCE_MAPPING_MISSING",
            ),
            "GAME_DATA_MISSING": ("GAME_DATA_MISSING", "INVALID_ACCOUNT_STATE"),
        }
        for issue in issues:
            source_codes_for_issue = source_map.get(issue["code"], (issue["code"],))
            found = [
                unresolved_by_code[code]
                for code in source_codes_for_issue
                if code in unresolved_by_code
            ]
            if not found:
                continue
            characters = [key for group in found for key in group["characters"]]
            messages = [message for group in found for message in group["messages"]]
            issue["details"].setdefault("characters", sorted(set(characters)))
            if messages:
                issue["details"].setdefault("plannerMessages", sorted(set(messages)))

    for message in backend_errors:
        add("BACKEND_ERROR", "ERROR", 1, "RETRY", {"message": message})

    if not account_available:
        add(
            "BACKEND_ERROR",
            "ERROR",
            1,
            "RETRY",
            {"message": "Local account record is unavailable."},
        )

    missing_characters = sorted(set(missing_character_keys))
    missing_weapons = sorted(set(missing_weapon_keys))
    add(
        "GAME_DATA_CHARACTER_COVERAGE",
        "WARNING",
        len(missing_characters),
        "UPDATE_GAME_DATA",
        {"characterKeys": missing_characters},
    )
    add(
        "GAME_DATA_WEAPON_COVERAGE",
        "WARNING",
        len(missing_weapons),
        "UPDATE_GAME_DATA",
        {"weaponKeys": missing_weapons},
    )

    for issue in issues:
        issue.setdefault(
            "decisionImpact",
            DECISION_IMPACT.get(
                issue["code"],
                "Dữ liệu này có thể làm thay đổi độ chính xác của quyết định hiện tại.",
            ),
        )

    status = (
        "ERROR"
        if any(item["severity"] == "ERROR" for item in issues)
        else "WARNING"
        if any(item["severity"] == "WARNING" for item in issues)
        else "READY"
    )
    counts = {
        "issues": sum(item["count"] for item in issues),
        "errors": sum(item["count"] for item in issues if item["severity"] == "ERROR"),
        "warnings": sum(
            item["count"] for item in issues if item["severity"] == "WARNING"
        ),
        "info": sum(item["count"] for item in issues if item["severity"] == "INFO"),
    }
    return {"status": status, "counts": counts, "issues": issues}
