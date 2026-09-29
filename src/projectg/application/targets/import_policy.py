"""Target import parsing, preview, and selection policy."""

from __future__ import annotations

from projectg.application.targets.errors import TargetOperationError
from projectg.domain.targets.validation import TargetValidationViolation, validate_target


class _ImportShapeViolation(ValueError):
    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def _object(value: object, field: str, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise _ImportShapeViolation(field or "root")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise _ImportShapeViolation(f"{field}.{sorted(missing)[0]}".strip("."))
    if extra:
        raise _ImportShapeViolation(f"{field}.{sorted(extra)[0]}".strip("."))
    return value


def _nonempty_key(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _ImportShapeViolation(field)
    return value.strip()


def _target_import_shape(payload: object) -> dict:
    body = _object(payload, "", {"version", "targets"})
    if type(body["version"]) is not int or body["version"] != 1:
        raise _ImportShapeViolation("version")
    targets = body["targets"]
    if not isinstance(targets, dict):
        raise _ImportShapeViolation("targets")
    normalized = {}
    for key, value in targets.items():
        normalized_key = _nonempty_key(key, "targets")
        if normalized_key in normalized:
            raise _ImportShapeViolation("targets")
        normalized[normalized_key] = value
    return {"version": 1, "targets": normalized}


def build_target_import_preview(
    payload: object,
    available: set[str] | frozenset[str],
    latest_versions: dict[str, int],
) -> tuple[dict, dict[str, dict]]:
    """Validate independent target rows and build a non-persistent MERGE preview."""
    if not isinstance(payload, dict):
        raise TargetOperationError(
            "INVALID_TARGET_IMPORT", "Target import must be an object.", {"field": "root"}
        )
    try:
        body = _target_import_shape(payload)
    except _ImportShapeViolation as exc:
        raise TargetOperationError(
            "INVALID_TARGET_IMPORT",
            "Target import has an invalid top-level field.",
            {"field": exc.field or "root"},
        ) from exc

    imported = body["targets"]
    if not imported:
        raise TargetOperationError(
            "INVALID_TARGET_IMPORT", "At least one target is required.", {"field": "targets"}
        )

    unknown = sorted(key for key in imported if key not in available)
    valid: dict[str, dict] = {}
    invalid = []
    for key, value in imported.items():
        try:
            checked = validate_target(value)
        except TargetValidationViolation as exc:
            invalid.append({"characterKey": key, "field": exc.field, "message": exc.message})
            continue
        if key in available:
            valid[key] = checked

    overwrites = [
        {
            "characterKey": key,
            "currentVersion": latest_versions[key],
            "newVersion": latest_versions[key] + 1,
        }
        for key in sorted(valid)
        if key in latest_versions
    ]
    overwrite_versions = {item["characterKey"]: item["currentVersion"] for item in overwrites}
    new_versions = [
        {
            "characterKey": key,
            "newVersion": latest_versions[key] + 1 if key in latest_versions else 1,
        }
        for key in sorted(valid)
    ]
    preview = {
        "mode": "MERGE",
        "validTargets": sorted(valid),
        "unknownCharacters": unknown,
        "invalidTargets": invalid,
        "overwrites": overwrites,
        "validTargetDetails": [
            {
                "characterKey": key,
                "currentVersion": overwrite_versions.get(key),
                "target": valid[key],
            }
            for key in sorted(valid)
        ],
        "newTargetVersions": new_versions,
        "willCreateOrUpdate": len(valid),
        "canImport": bool(valid),
    }
    if not valid and invalid:
        raise TargetOperationError(
            "EMPTY_TARGET_IMPORT",
            "No valid target entries were available to import.",
            preview,
        )
    return preview, valid


def select_target_import(
    valid: dict[str, dict], selected_keys: set[str] | frozenset[str], preview: dict
) -> dict[str, dict]:
    selected = set(selected_keys)
    if not selected or not selected <= set(valid):
        raise TargetOperationError(
            "EMPTY_TARGET_IMPORT", "No owned valid targets were selected.", preview
        )
    return {key: valid[key] for key in sorted(selected)}


def validate_operation_id(operation_id: object) -> str:
    if not isinstance(operation_id, str) or not 16 <= len(operation_id) <= 128:
        raise TargetOperationError(
            "INVALID_IDEMPOTENCY_KEY",
            "Import operation key is invalid.",
            {"field": "idempotencyKey"},
        )
    return operation_id
