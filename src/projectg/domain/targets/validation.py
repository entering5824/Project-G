"""Strict, framework-free validation for character target values."""

from __future__ import annotations

import math

from projectg.domain.targets.rules import TargetRuleViolation, validate_target_rules


class TargetValidationViolation(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.message = message
        self.field = field


class _TargetShapeViolation(ValueError):
    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def _object(value: object, field: str, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise _TargetShapeViolation(field or "root")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise _TargetShapeViolation(f"{field}.{sorted(missing)[0]}".strip("."))
    if extra:
        raise _TargetShapeViolation(f"{field}.{sorted(extra)[0]}".strip("."))
    return value


def _strict_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise _TargetShapeViolation(field)
    return value


def _strict_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise _TargetShapeViolation(field)
    return value


def _finite_number(value: object, field: str) -> float:
    if type(value) not in (int, float):
        raise _TargetShapeViolation(field)
    try:
        normalized = float(value)
    except (OverflowError, ValueError):
        raise _TargetShapeViolation(field) from None
    if not math.isfinite(normalized):
        raise _TargetShapeViolation(field)
    return normalized


def _nonempty_key(value: object, field: str, maximum: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _TargetShapeViolation(field)
    result = value.strip()
    if maximum is not None and len(result) > maximum:
        raise _TargetShapeViolation(field)
    return result


def _character_target_shape(value: object) -> dict:
    root = _object(
        value,
        "",
        {"level", "ascension", "importance", "talents", "weapon", "artifact", "notes"},
    )
    result = dict(root)
    for field in ("level", "ascension"):
        result[field] = _strict_int(root[field], field)

    importance = _object(root["importance"], "importance", {"level", "ascension"})
    result["importance"] = {
        key: _finite_number(importance[key], f"importance.{key}")
        for key in ("level", "ascension")
    }

    talents = _object(root["talents"], "talents", {"normal", "skill", "burst"})
    result["talents"] = {}
    for name in ("normal", "skill", "burst"):
        field = f"talents.{name}"
        item = _object(talents[name], field, {"enabled", "target", "importance"})
        result["talents"][name] = {
            "enabled": _strict_bool(item["enabled"], f"{field}.enabled"),
            "target": _strict_int(item["target"], f"{field}.target"),
            "importance": _finite_number(item["importance"], f"{field}.importance"),
        }

    weapon = _object(root["weapon"], "weapon", {"targetLevel", "importance"}, {"weaponKey"})
    result["weapon"] = {
        "weaponKey": None
        if weapon.get("weaponKey") is None
        else _nonempty_key(weapon["weaponKey"], "weapon.weaponKey"),
        "targetLevel": _strict_int(weapon["targetLevel"], "weapon.targetLevel"),
        "importance": _finite_number(weapon["importance"], "weapon.importance"),
    }

    artifact = _object(
        root["artifact"],
        "artifact",
        {"enabled", "targetQuality", "importance", "primarySets", "alternativeSets"},
        {"gate"},
    )
    quality = artifact["targetQuality"]
    if not isinstance(quality, str) or quality not in ("ACCEPTABLE", "GOOD", "EXCELLENT"):
        raise _TargetShapeViolation("artifact.targetQuality")

    sets = {}
    for name in ("primarySets", "alternativeSets"):
        values = artifact[name]
        if not isinstance(values, list) or len(values) > 20:
            raise _TargetShapeViolation(f"artifact.{name}")
        sets[name] = [_nonempty_key(item, f"artifact.{name}", 128) for item in values]
    if len(set(sets["primarySets"] + sets["alternativeSets"])) != len(
        sets["primarySets"] + sets["alternativeSets"]
    ):
        raise _TargetShapeViolation("artifact.alternativeSets")

    gate = _object(
        artifact.get("gate", {}),
        "artifact.gate",
        set(),
        {"minLevel", "minAscension", "weaponMinLevel", "requiredTalents"},
    )
    normalized_gate = {
        "minLevel": None
        if gate.get("minLevel") is None
        else _strict_int(gate["minLevel"], "artifact.gate.minLevel"),
        "minAscension": None
        if gate.get("minAscension") is None
        else _strict_int(gate["minAscension"], "artifact.gate.minAscension"),
        "weaponMinLevel": None
        if gate.get("weaponMinLevel") is None
        else _strict_int(gate["weaponMinLevel"], "artifact.gate.weaponMinLevel"),
        "requiredTalents": gate.get("requiredTalents", []),
    }
    required_talents = normalized_gate["requiredTalents"]
    if not isinstance(required_talents, list) or any(
        not isinstance(name, str) or name not in ("normal", "skill", "burst")
        for name in required_talents
    ):
        raise _TargetShapeViolation("artifact.gate.requiredTalents")

    result["artifact"] = {
        "enabled": _strict_bool(artifact["enabled"], "artifact.enabled"),
        "targetQuality": quality,
        "importance": _finite_number(artifact["importance"], "artifact.importance"),
        **sets,
        "gate": normalized_gate,
    }
    notes = root["notes"]
    if not isinstance(notes, str) or len(notes) > 2000:
        raise _TargetShapeViolation("notes")
    result["notes"] = notes
    return result


def validate_target(value: object) -> dict:
    """Normalize a target and reject invalid shape or unreachable progression."""
    try:
        data = _character_target_shape(value)
    except _TargetShapeViolation as exc:
        raise TargetValidationViolation(
            "Target body has a missing or invalid field.", exc.field or "target"
        ) from exc
    try:
        validate_target_rules(data)
    except TargetRuleViolation as exc:
        raise TargetValidationViolation(exc.message, exc.field) from exc
    return data
