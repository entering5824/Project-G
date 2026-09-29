"""Application projection for account history."""

from projectg.application.ports.outbound.support_gateway import HistoryContext, SupportData


def build_history_view(context: HistoryContext, limit: int) -> SupportData:
    snapshots = [
        {
            "id": row.id,
            "when": row.when,
            "source": "SNAPSHOT",
            "event": "SNAPSHOT_IMPORTED",
            "character": None,
            "current": row.current,
            "previousSnapshotId": row.previous_snapshot_id,
            "snapshotIndex": row.snapshot_index,
        }
        for row in context.snapshots
    ]
    events = [
        {
            "id": row.id,
            "when": row.when,
            "source": row.source,
            "event": row.event,
            "character": row.character,
            "snapshotId": row.snapshot_id,
            "payload": row.payload,
        }
        for row in context.events
    ]
    items = sorted(
        [*snapshots, *events],
        key=lambda row: (row["when"], row.get("id") or ""),
        reverse=True,
    )[:limit]
    groups = {
        "accountProgress": [row for row in items if row["source"] == "SNAPSHOT"],
        "targetConfigChanges": [row for row in items if row["source"] == "CONFIG"],
        "completionChanges": [row for row in items if row["source"] == "DERIVED"],
    }
    return SupportData({
        "items": items,
        "groups": groups,
        "snapshots": snapshots,
        "currentSnapshotId": context.current_snapshot_id,
    })
