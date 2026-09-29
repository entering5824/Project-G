"""Verify the Akasha RV import against both ProjectG snapshots."""

import csv
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "runtime" / "akasha_rv_verified_matches_840263475.csv"
OLD = "7e5bbf10-868c-4eba-89fb-83470c230fcd"
NEW = "4dc1b4af-7525-4b7e-b318-a71d73ba7c92"
DB = Path(os.environ["LOCALAPPDATA"]) / "GenshinPlanner" / "app.db"


def main() -> None:
    with REPORT.open(encoding="utf-8", newline="") as source:
        expected = {row["artifact_instance_id"]: float(row["akasha_rv"])
                    for row in csv.DictReader(source)}
    assert len(expected) == 87
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        active = db.execute("SELECT current_snapshot_id FROM accounts WHERE id='main'").fetchone()[0]
        assert active == NEW, active
        def artifacts(snapshot_id):
            rows = db.execute("SELECT * FROM snapshot_artifacts WHERE snapshot_id=?", (snapshot_id,))
            return {row["artifact_instance_id"]: dict(row) for row in rows}
        old, new = artifacts(OLD), artifacts(NEW)
        assert old.keys() == new.keys()
        changed_rv = set()
        for artifact_id, before in old.items():
            after = new[artifact_id]
            for key in before.keys() - {"snapshot_id", "rv", "rv_status"}:
                assert before[key] == after[key], (artifact_id, key)
            if (before["rv"], before["rv_status"]) != (after["rv"], after["rv_status"]):
                changed_rv.add(artifact_id)
            if artifact_id in expected:
                assert after["rv"] == expected[artifact_id], artifact_id
                assert after["rv_status"] == "IMPORTED", artifact_id
        assert changed_rv <= expected.keys(), sorted(changed_rv - expected.keys())
        def count(table, snapshot_id):
            return db.execute(f"SELECT COUNT(*) FROM {table} WHERE snapshot_id=?", (snapshot_id,)).fetchone()[0]
        counts = {table: (count(table, OLD), count(table, NEW))
                  for table in ("snapshot_characters", "snapshot_weapons", "snapshot_artifacts", "snapshot_teams")}
        assert all(a == b for a, b in counts.values()), counts
        print({"activeSnapshot": active, "matchedRV": len(expected),
               "changedRV": len(changed_rv), "counts": counts})


if __name__ == "__main__":
    main()
