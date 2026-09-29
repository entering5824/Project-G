from dataclasses import dataclass, field, replace
from math import isfinite


WEIGHT_KEYS = ("deficiency", "importance", "tier", "team", "completion")


@dataclass(frozen=True)
class PlannerConfig:
    planner_version: str = "1.0.0"
    config_version: str = "1"
    horizon: int = 20
    reorder_threshold: float = 3.0
    manual_order_enabled: bool = False
    manual_order: tuple[str, ...] = ()
    tier_fallback: float = 0.70
    team_primary: float = 1.00
    team_saved: float = 0.75
    team_none: float = 0.50
    priority_normal: float = 1.00
    priority_prioritized: float = 1.15
    priority_deprioritized: float = 0.85
    efficiency_modifier_base: float = 0.85
    efficiency_modifier_weight: float = 0.15
    confidence: float = 1.00
    efficiency: float = 1.00
    weights: dict[str, float] = field(default_factory=lambda: {
        "deficiency": 0.32,
        "importance": 0.28,
        "tier": 0.18,
        "team": 0.12,
        "completion": 0.10,
    })
    level_milestones: tuple[int, ...] = (1, 20, 40, 50, 60, 70, 80, 90)
    weapon_milestones: tuple[int, ...] = (1, 20, 40, 50, 60, 70, 80, 90)
    # Minimum character ascension phase at which a naturally invested talent
    # rank is available. GOOD talent values are base/invested values; they do
    # not include +3 constellation skill-level bonuses.
    talent_ascension_requirements: tuple[tuple[int, int], ...] = (
        (1, 0), (2, 2), (4, 3), (6, 4), (8, 5), (10, 6), (13, 6),
    )
    ascension_level_caps: tuple[int, ...] = (20, 40, 50, 60, 70, 80, 90)
    deterministic_completion_near_threshold: float = 0.75

    def priority_multiplier(self, override: str) -> float:
        return {
            "NORMAL": self.priority_normal,
            "PRIORITIZED": self.priority_prioritized,
            "DEPRIORITIZED": self.priority_deprioritized,
        }.get(override, self.priority_normal)


DEFAULT_PLANNER_CONFIG = PlannerConfig()


def config_payload(config: PlannerConfig) -> dict:
    return {
        "weights": {key: float(config.weights[key]) for key in WEIGHT_KEYS},
        "tierFallback": config.tier_fallback,
        "teamPrimary": config.team_primary,
        "teamSaved": config.team_saved,
        "teamNone": config.team_none,
        "priorityOverride": {
            "normal": config.priority_normal,
            "prioritized": config.priority_prioritized,
            "deprioritized": config.priority_deprioritized,
        },
        "completionNearThreshold": config.deterministic_completion_near_threshold,
        "horizon": config.horizon,
        "reorderThreshold": config.reorder_threshold,
        "manualOrderEnabled": config.manual_order_enabled,
        "manualOrder": list(config.manual_order),
    }


def config_from_payload(
    payload: dict,
    version: int | str,
    base: PlannerConfig | None = None,
) -> PlannerConfig:
    if not isinstance(payload, dict):
        raise ValueError("Planner config must be an object.")

    current = config_payload(base or DEFAULT_PLANNER_CONFIG)
    weights = payload.get("weights", current["weights"])
    if not isinstance(weights, dict) or set(weights) != set(WEIGHT_KEYS):
        raise ValueError("weights must define deficiency, importance, tier, team, and completion.")

    parsed: dict[str, float] = {}
    for key in WEIGHT_KEYS:
        value = weights[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
            or not 0 <= float(value) <= 1
        ):
            raise ValueError(f"weights.{key} must be between 0 and 1.")
        parsed[key] = float(value)
    if abs(sum(parsed.values()) - 1.0) > 1e-6:
        raise ValueError("Planner weights must sum to 1.0.")

    override = payload.get("priorityOverride", current["priorityOverride"])
    if not isinstance(override, dict) or set(override) != {"normal", "prioritized", "deprioritized"}:
        raise ValueError("priorityOverride must define normal, prioritized, and deprioritized.")

    def bounded(name: str, minimum: float = 0.0, maximum: float = 1.0) -> float:
        value = payload.get(name, current[name])
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
            or not minimum <= float(value) <= maximum
        ):
            raise ValueError(f"{name} must be between {minimum} and {maximum}.")
        return float(value)

    multipliers: dict[str, float] = {}
    for key in ("normal", "prioritized", "deprioritized"):
        value = override[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
            or not 0.01 <= float(value) <= 3.0
        ):
            raise ValueError(f"priorityOverride.{key} must be between 0.01 and 3.0.")
        multipliers[key] = float(value)

    horizon = payload.get("horizon", current["horizon"])
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 100:
        raise ValueError("horizon must be an integer between 1 and 100.")

    reorder = payload.get("reorderThreshold", current["reorderThreshold"])
    if (
        isinstance(reorder, bool)
        or not isinstance(reorder, (int, float))
        or not isfinite(float(reorder))
        or float(reorder) < 0
    ):
        raise ValueError("reorderThreshold must be a non-negative number.")

    manual_enabled = payload.get("manualOrderEnabled", current["manualOrderEnabled"])
    if not isinstance(manual_enabled, bool):
        raise ValueError("manualOrderEnabled must be a boolean.")
    manual_order = payload.get("manualOrder", current["manualOrder"])
    if not isinstance(manual_order, list) or any(
        not isinstance(item, str) or not item.strip() for item in manual_order
    ):
        raise ValueError("manualOrder must be a list of non-empty character keys.")
    normalized_manual_order = [item.strip() for item in manual_order]
    if len(normalized_manual_order) != len(set(normalized_manual_order)):
        raise ValueError("manualOrder cannot contain duplicate character keys.")

    return replace(
        base or DEFAULT_PLANNER_CONFIG,
        config_version=str(version),
        weights=parsed,
        tier_fallback=bounded("tierFallback"),
        team_primary=bounded("teamPrimary"),
        team_saved=bounded("teamSaved"),
        team_none=bounded("teamNone"),
        priority_normal=multipliers["normal"],
        priority_prioritized=multipliers["prioritized"],
        priority_deprioritized=multipliers["deprioritized"],
        deterministic_completion_near_threshold=bounded("completionNearThreshold"),
        horizon=horizon,
        reorder_threshold=float(reorder),
        manual_order_enabled=manual_enabled,
        manual_order=tuple(normalized_manual_order),
    )
