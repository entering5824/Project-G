from projectg.application.backups.models import (
    BackupExportResult,
    BackupManifest,
    BackupRestoreResult,
)
from projectg.application.ports.outbound.support_gateway import (
    HistoryContext,
    HistoryEventFact,
    HistorySnapshotFact,
    LogDirectory,
    SupportData,
)
from projectg.application.use_cases.backups.create_backup import CreateBackup, CreateBackupRequest
from projectg.application.use_cases.backups.restore_backup import RestoreBackup, RestoreBackupRequest
from projectg.application.use_cases.support.compare_history import CompareHistory, CompareHistoryRequest
from projectg.application.use_cases.support.get_history import GetHistory
from projectg.application.use_cases.support.get_logs_directory import GetLogsDirectory


class FakeSupportGateway:
    def __init__(self):
        self.calls = []

    def load_history(self, limit):
        self.calls.append(("history", limit))
        return HistoryContext(
            snapshots=(HistorySnapshotFact("snap-1", "2026-09-01T00:00:00", True, None, 1),),
            events=(HistoryEventFact(
                "event-1", "2026-09-02T00:00:00", "CONFIG", "TARGET_CHANGED",
                "Amber", "snap-1", {"x": 1}),),
            current_snapshot_id="snap-1",
        )

    def compare_history(self, before, after):
        self.calls.append(("compare", before, after))
        return SupportData({"characters": []})

    def logs_directory(self):
        self.calls.append(("logs",))
        return LogDirectory("logs")


class FakeBackupGateway:
    def __init__(self):
        self.calls = []
        self.manifest = BackupManifest(
            backup_schema_version=2,
            app_version="0.1.0",
            database_schema_version="0017_remove_inventory",
            exported_at="2026-09-26T00:00:00+00:00",
            reason="MANUAL_EXPORT",
            includes_akasha_images=False,
            snapshot_file_count=0,
            akasha_file_count=0,
            files={},
        )

    def create_manual(self, destination):
        self.calls.append(("backup", destination))
        return BackupExportResult(destination, self.manifest)

    def restore(self, source):
        self.calls.append(("restore", source))
        return BackupRestoreResult(self.manifest, "pre.zip")


def test_support_and_backup_use_cases_use_separate_ports():
    support = FakeSupportGateway()
    backup = FakeBackupGateway()

    history = GetHistory(support).execute(5).values
    assert history["currentSnapshotId"] == "snap-1"
    assert history["items"][0]["event"] == "TARGET_CHANGED"
    assert history["groups"]["targetConfigChanges"][0]["id"] == "event-1"
    assert CompareHistory(support).execute(CompareHistoryRequest("a", "b")).values == {"characters": []}
    assert CreateBackup(backup).execute(CreateBackupRequest("out.zip")).values == {
        "path": "out.zip", "exportedAt": "2026-09-26T00:00:00+00:00"}
    restored = RestoreBackup(backup).execute(RestoreBackupRequest("in.zip")).values
    assert restored["restored"] is True
    assert restored["preRestoreBackup"] == "pre.zip"
    assert GetLogsDirectory(support).execute().path == "logs"

    assert support.calls == [("history", 5), ("compare", "a", "b"), ("logs",)]
    assert backup.calls == [("backup", "out.zip"), ("restore", "in.zip")]


def test_history_projection_sorts_sources_and_applies_display_limit():
    class MixedGateway(FakeSupportGateway):
        def load_history(self, limit):
            return HistoryContext(
                snapshots=(
                    HistorySnapshotFact("s1", "2026-09-01T00:00:00", False, None, 1),
                    HistorySnapshotFact("s2", "2026-09-03T00:00:00", True, "s1", 2),
                ),
                events=(
                    HistoryEventFact("c1", "2026-09-04T00:00:00", "CONFIG", "TARGET_CHANGED", None, "s2", {}),
                    HistoryEventFact("d1", "2026-09-02T00:00:00", "DERIVED", "CHARACTER_COMPLETED", "Amber", "s1", {}),
                ),
                current_snapshot_id="s2",
            )

    result = GetHistory(MixedGateway()).execute(3).values
    assert [row["id"] for row in result["items"]] == ["c1", "s2", "d1"]
    assert [row["id"] for row in result["groups"]["targetConfigChanges"]] == ["c1"]
    assert [row["id"] for row in result["groups"]["completionChanges"]] == ["d1"]
