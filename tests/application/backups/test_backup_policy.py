from datetime import datetime, timedelta, timezone

import pytest

from projectg.application.backups.errors import BackupError
from projectg.application.backups.models import AutomaticBackupCandidate
from projectg.application.backups.policy import (
    DB_SCHEMA_HEAD,
    parse_backup_manifest,
    select_automatic_backups_to_keep,
)


def manifest(**overrides):
    value = {
        "backupSchemaVersion": 2,
        "appVersion": "0.1.0",
        "databaseSchemaVersion": DB_SCHEMA_HEAD,
        "exportedAt": "2026-09-26T00:00:00+00:00",
        "reason": "MANUAL_EXPORT",
        "includesAkashaImages": False,
        "snapshotFileCount": 1,
        "akashaFileCount": 0,
        "files": {
            "database.sqlite": {"sha256": "a" * 64, "sizeBytes": 12},
            "settings.json": {"sha256": "b" * 64, "sizeBytes": 5},
        },
    }
    value.update(overrides)
    return value


def test_manifest_policy_returns_typed_model_and_rejects_future_schema():
    parsed = parse_backup_manifest(manifest())
    assert parsed.database_schema_version == DB_SCHEMA_HEAD
    assert parsed.files["database.sqlite"].size_bytes == 12

    with pytest.raises(BackupError) as exc:
        parse_backup_manifest(manifest(databaseSchemaVersion="9999_future"))
    assert exc.value.code == "BACKUP_SCHEMA_INCOMPATIBLE"


def test_manifest_policy_rejects_malformed_integrity_entry():
    value = manifest()
    value["files"]["database.sqlite"]["sha256"] = "not-a-hash"
    with pytest.raises(BackupError) as exc:
        parse_backup_manifest(value)
    assert exc.value.code == "BACKUP_INTEGRITY_MANIFEST_INVALID"


def test_retention_policy_is_pure_and_keeps_recent_daily_weekly_union():
    anchor = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
    candidates = tuple(
        AutomaticBackupCandidate(f"auto-{age}", (anchor - timedelta(days=age)).timestamp())
        for age in range(40)
    )
    retained = select_automatic_backups_to_keep(
        candidates, keep_last=2, keep_daily=3, keep_weekly=4)
    assert {"auto-0", "auto-1"} <= retained
    assert "auto-2" in retained
    assert len(retained) >= 4
    assert "auto-39" not in retained
