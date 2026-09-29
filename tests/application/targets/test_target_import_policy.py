import pytest

from projectg.application.targets.errors import TargetOperationError
from projectg.application.targets.import_policy import (
    build_target_import_preview,
    select_target_import,
    validate_operation_id,
)


def _target():
    return {
        "level": 80,
        "ascension": 5,
        "importance": {"level": 0.8, "ascension": 0.8},
        "talents": {
            name: {"enabled": False, "target": 1, "importance": 0.0}
            for name in ("normal", "skill", "burst")
        },
        "weapon": {"targetLevel": 1, "importance": 0.0},
        "artifact": {
            "enabled": False,
            "targetQuality": "GOOD",
            "importance": 0.0,
            "primarySets": [],
            "alternativeSets": [],
            "gate": {},
        },
        "notes": "",
    }


def test_preview_is_application_policy_not_database_behavior():
    payload = {
        "version": 1,
        "targets": {"Amber": _target(), "Unknown": _target(), "Lisa": []},
    }

    preview, valid = build_target_import_preview(
        payload, {"Amber", "Lisa"}, {"Amber": 3}
    )

    assert set(valid) == {"Amber"}
    assert preview["unknownCharacters"] == ["Unknown"]
    assert preview["invalidTargets"][0]["characterKey"] == "Lisa"
    assert preview["overwrites"] == [
        {"characterKey": "Amber", "currentVersion": 3, "newVersion": 4}
    ]


def test_selection_rejects_keys_outside_valid_preview():
    preview, valid = build_target_import_preview(
        {"version": 1, "targets": {"Amber": _target()}}, {"Amber"}, {}
    )

    with pytest.raises(TargetOperationError) as error:
        select_target_import(valid, {"Lisa"}, preview)

    assert error.value.code == "EMPTY_TARGET_IMPORT"


def test_operation_id_policy_is_owned_by_application():
    with pytest.raises(TargetOperationError) as error:
        validate_operation_id("short")

    assert error.value.code == "INVALID_IDEMPOTENCY_KEY"
