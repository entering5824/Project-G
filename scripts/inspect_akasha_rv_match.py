"""Read-only comparison of Akasha RV rows and the active desktop snapshot."""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "runtime" / "akasha_rv_840263475.csv"
DB = Path(os.environ["LOCALAPPDATA"]) / "GenshinPlanner" / "app.db"


def key(name: str) -> str:
    if name == "Nhà Lữ Hành":
        return "TravelerAnemo"
    return name.replace(" ", "")


def main() -> None:
    selected = set(sys.argv[1:])
    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        values = list(csv.DictReader(source))
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as db:
        sid = db.execute("select current_snapshot_id from accounts where id='main'").fetchone()[0]
        if "--json" in selected:
            result = {}
            for item in values:
                name = item["name"]
                rows = db.execute(
                    "select slot_key,artifact_instance_id,substats_json from snapshot_artifacts "
                    "where snapshot_id=? and character_key=?",
                    (sid, key(name)),
                ).fetchall()
                result[name] = {
                    slot: [iid, sorted(
                        [str(s["value"]) + ("%" if s["key"].endswith("_") else "")
                         for s in json.loads(raw) if s.get("key")],
                    )] for slot, iid, raw in rows
                }
            print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
            return
        for item in values:
            name = item["name"]
            if selected and name not in selected:
                continue
            rows = db.execute(
                "select slot_key, artifact_instance_id, level, main_stat_key, substats_json, rv, rv_status "
                "from snapshot_artifacts where snapshot_id=? and character_key=? order by slot_key",
                (sid, key(name)),
            ).fetchall()
            print(name, "akasha", item["total"] or "none", "current", len(rows))
            for slot, iid, level, main_stat, raw_substats, rv, status in rows:
                subs = [(s.get("key"), s.get("value")) for s in json.loads(raw_substats)]
                print(" ", slot, iid, level, main_stat, subs, rv, status,
                      "akasha", item.get(slot) or "none")


if __name__ == "__main__":
    main()
