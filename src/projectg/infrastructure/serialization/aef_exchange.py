"""Strict AEF v1 parsing and normalization for externally extracted values."""
from __future__ import annotations

from math import isfinite

from projectg.application.artifacts.errors import ArtifactDocumentError
from projectg.application.ports.outbound.artifact_document_parser import ParsedArtifactEvaluation
from projectg.domain.artifacts.validation import validate_metrics

AEF_FORMAT = "AEF"
AEF_VERSION = 1
SLOT_KEYS = {"flower", "plume", "sands", "goblet", "circlet"}
ROOT_KEYS = {"format", "version", "characterKey", "source", "metrics"}
METRIC_KEYS = {"rv", "cv", "rankPercent", "customScore", "slots", "extra"}


ExchangeError = ArtifactDocumentError


def _object(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ExchangeError("INVALID_AEF", f"{label} must be a JSON object.", label)
    return value


def normalize_metrics(payload: dict) -> dict:
    metrics = _object(payload, "metrics")
    unknown = set(metrics) - METRIC_KEYS
    if unknown:
        raise ExchangeError("UNKNOWN_AEF_FIELD", f"Unknown metrics fields: {', '.join(sorted(unknown))}.", "metrics")
    normalized = {}
    for source, target in (("rv", "rv"), ("cv", "cv"), ("rankPercent", "rank_percent"),
                           ("customScore", "custom_score")):
        if source in metrics:
            normalized[target] = metrics[source]
    if "slots" in metrics:
        slots = _object(metrics["slots"], "metrics.slots")
        unknown_slots = set(slots) - SLOT_KEYS
        if unknown_slots:
            raise ExchangeError("UNKNOWN_AEF_SLOT", f"Unknown artifact slots: {', '.join(sorted(unknown_slots))}.", "metrics.slots")
        normalized["slots"] = slots
    if "extra" in metrics:
        extra = _object(metrics["extra"], "metrics.extra")
        for key, value in extra.items():
            if not isinstance(key, str) or not key or isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or float(value) < 0:
                raise ExchangeError("INVALID_AEF_EXTRA", "metrics.extra values must be finite, non-negative numbers.", f"metrics.extra.{key}")
        normalized["extra_metrics"] = extra
    try:
        return validate_metrics(normalized)
    except ValueError as exc:
        raise ExchangeError("INVALID_AEF_METRICS", str(exc), "metrics") from exc


def _validate_row(payload: dict, index: int) -> dict:
    row = _object(payload, f"evaluations[{index}]")
    unknown = set(row) - ROOT_KEYS
    if unknown:
        raise ExchangeError("UNKNOWN_AEF_FIELD", f"Unknown fields: {', '.join(sorted(unknown))}.")
    if row.get("format") != AEF_FORMAT:
        raise ExchangeError("INVALID_AEF_FORMAT", "format must be AEF.", "format")
    if not isinstance(row.get("version"), int) or isinstance(row.get("version"), bool) or row.get("version") != AEF_VERSION:
        raise ExchangeError("UNSUPPORTED_AEF_VERSION", f"Only AEF version {AEF_VERSION} is supported.", "version")
    source = row.get("source", "ASSISTED_MANUAL")
    if source != "ASSISTED_MANUAL":
        raise ExchangeError("INVALID_AEF_SOURCE", "source must be ASSISTED_MANUAL.", "source")
    key = row.get("characterKey")
    if not isinstance(key, str) or not key.strip():
        raise ExchangeError("INVALID_CHARACTER_KEY", "characterKey is required and must be a canonical character key.", "characterKey")
    raw_metrics = normalize_metrics(row.get("metrics"))
    return {"index": index, "characterKey": key.strip(), "metrics": raw_metrics}


def parse_exchange(payload) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
        if not rows:
            raise ExchangeError("INVALID_AEF_BULK", "AEF array must contain at least one evaluation.", "evaluations")
    else:
        root = _object(payload, "AEF payload")
        if "evaluations" in root:
            unknown = set(root) - {"format", "version", "evaluations"}
            if unknown:
                raise ExchangeError("UNKNOWN_AEF_FIELD", f"Unknown bulk fields: {', '.join(sorted(unknown))}.")
            if root.get("format") != AEF_FORMAT:
                raise ExchangeError("INVALID_AEF_FORMAT", "format must be AEF.", "format")
            if not isinstance(root.get("version"), int) or isinstance(root.get("version"), bool) or root.get("version") != AEF_VERSION:
                raise ExchangeError("UNSUPPORTED_AEF_VERSION", f"Only AEF version {AEF_VERSION} is supported.", "version")
            rows = root["evaluations"]
            if not isinstance(rows, list) or not rows:
                raise ExchangeError("INVALID_AEF_BULK", "evaluations must be a non-empty array.", "evaluations")
        else:
            rows = [root]
    parsed, errors = [], []
    for index, row in enumerate(rows):
        try:
            parsed.append(_validate_row(row, index))
        except ExchangeError as exc:
            errors.append({"index": index, "code": exc.code, "message": str(exc), "field": exc.field})
    seen: dict[str, list[int]] = {}
    for row in parsed:
        seen.setdefault(row["characterKey"], []).append(row["index"])
    duplicates = {key: indexes for key, indexes in seen.items() if len(indexes) > 1}
    for key, indexes in duplicates.items():
        for index in indexes:
            errors.append({"index": index, "code": "DUPLICATE_CHARACTER_EVALUATION",
                "message": f"Character {key} appears more than once in this batch.", "field": "characterKey"})
    return [{**row, "errors":[error for error in errors if error["index"] == row["index"]]}
            for row in parsed] + [{"index":error["index"],"characterKey":None,"metrics":None,"errors":[error]}
            for error in errors if error["index"] not in {row["index"] for row in parsed}]


class AefArtifactDocumentParser:
    """Infrastructure adapter for strict AEF v1 payload parsing."""

    def parse(self, payload: object) -> tuple[ParsedArtifactEvaluation, ...]:
        rows = parse_exchange(payload)
        return tuple(
            ParsedArtifactEvaluation(
                index=int(row["index"]),
                character_key=row.get("characterKey"),
                metrics=row.get("metrics"),
                errors=tuple(dict(error) for error in row.get("errors", ())),
            )
            for row in rows
        )
