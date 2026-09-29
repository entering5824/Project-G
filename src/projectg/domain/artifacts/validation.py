"""Pure validation rules for artifact evaluation input."""

from math import isfinite

from projectg.domain.artifacts.models import ArtifactQualityConfig, QUALITY_LABELS

def validate_quality_config(payload: dict, version: int = 0) -> ArtifactQualityConfig:
    if not isinstance(payload, dict):
        raise ValueError("Artifact quality config must be an object.")
    adapter = payload.get("adapterType", "rv")
    if adapter not in {"rv", "cv", "rank_percent", "custom_score"}:
        raise ValueError("adapterType must be rv, cv, rank_percent, or custom_score.")
    thresholds = payload.get("thresholds", {})
    if not isinstance(thresholds, dict) or set(thresholds) != set(QUALITY_LABELS):
        raise ValueError("thresholds must define POOR, ACCEPTABLE, GOOD, and EXCELLENT.")
    values = []
    parsed = {}
    for label in QUALITY_LABELS:
        value = thresholds[label]
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or float(value) < 0:
                raise ValueError(f"thresholds.{label} must be a non-negative finite number or null.")
            value = float(value)
            if adapter == "rank_percent" and value > 100:
                raise ValueError(f"thresholds.{label} must be at most 100 for Akasha rankPercent.")
        parsed[label] = value
        values.append(value)
    if any(value is not None for value in values):
        if any(value is None for value in values):
            raise ValueError("Configure all four thresholds, or leave all four unset.")
        pairs = zip(values, values[1:])
        invalid_order = (any(left <= right for left, right in pairs) if adapter == "rank_percent"
                         else any(left >= right for left, right in pairs))
        if invalid_order:
            if adapter == "rank_percent":
                raise ValueError("Akasha top-percent thresholds must decrease strictly: POOR > ACCEPTABLE > GOOD > EXCELLENT.")
            raise ValueError("Thresholds must increase strictly: POOR < ACCEPTABLE < GOOD < EXCELLENT.")
    return ArtifactQualityConfig(version=version, adapter_type=adapter, thresholds=parsed)

def validate_metrics(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("metrics must be an object.")
    allowed = {"rv", "cv", "rank_percent", "custom_score", "extra_metrics", "slots", "developer_input", "normalized_score"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unknown metric fields: {', '.join(sorted(unknown))}.")
    result = {}
    for key in ("rv", "cv", "rank_percent", "custom_score", "normalized_score"):
        value = payload.get(key)
        if value is None:
            if key in payload:
                result[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"{key} must be a finite non-negative number.")
        if key == "rank_percent" and float(value) > 100:
            raise ValueError("rank_percent must be between 0 and 100.")
        result[key] = float(value)
    if "normalized_score" in result:
        if payload.get("developer_input") is not True:
            raise ValueError("normalized_score is allowed only with developer_input=true.")
        if result["normalized_score"] > 1:
            raise ValueError("normalized_score must be between 0 and 1.")
        result["developerInput"] = True
        result["developer_input"] = True
    extras = payload.get("extra_metrics", {})
    if not isinstance(extras, dict):
        raise ValueError("extra_metrics must be an object of numeric values.")
    normalized_extras = {}
    for key, value in extras.items():
        if not isinstance(key, str) or not key or isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError("extra_metrics must use named finite numeric values.")
        normalized_extras[key] = float(value)
    result["extraMetrics"] = normalized_extras
    slots = payload.get("slots", {})
    if not isinstance(slots, dict):
        raise ValueError("slots must be an object.")
    normalized_slots = {}
    for key, value in slots.items():
        if key not in {"flower", "plume", "sands", "goblet", "circlet"}:
            raise ValueError(f"Unknown artifact slot {key}.")
        if value is None:
            normalized_slots[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"slots.{key} must be finite and non-negative.")
        normalized_slots[key] = float(value)
    result["slots"] = normalized_slots
    if not any(key in payload for key in ("rv", "cv", "rank_percent", "custom_score", "normalized_score")) and not normalized_extras:
        raise ValueError("At least one overall metric is required.")
    return result
