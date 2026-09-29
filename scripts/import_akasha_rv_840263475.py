"""Import verified Akasha piece RV into the active ProjectG snapshot.

The Akasha profile and the local GOOD snapshot were compared by character,
slot, and all displayed substat values on 2026-09-29. Unmatched pieces are
left to ProjectG's existing RV calculation. Run --preview before --commit.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EXPECTED_SNAPSHOT = "7e5bbf10-868c-4eba-89fb-83470c230fcd"
SOURCE = ROOT / "data" / "runtime" / "akasha_rv_840263475.csv"
PAYLOAD = ROOT / "data" / "runtime" / "akasha_rv_verified_import_840263475.json"
REPORT = ROOT / "data" / "runtime" / "akasha_rv_verified_matches_840263475.csv"
SLOTS = ("flower", "plume", "sands", "goblet", "circlet")

# Exact substat matches against the active 2026-09-27 GOOD snapshot.
MATCHED = {
    "Yelan": "plume sands goblet circlet",
    "Raiden Shogun": "flower plume sands goblet circlet",
    "Mavuika": "flower plume sands goblet circlet",
    "Skirk": "flower plume sands goblet circlet",
    "Varesa": "flower plume sands goblet",
    "Hu Tao": "flower sands",
    "Eula": "flower plume sands circlet",
    "Odette": "flower plume sands goblet circlet",
    "Nefer": "flower plume sands goblet circlet",
    "Nahida": "flower plume sands goblet circlet",
    "Navia": "flower plume sands goblet circlet",
    "Vesna": "flower plume sands goblet circlet",
    "Xingqiu": "flower sands goblet circlet",
    "Columbina": "flower plume sands goblet circlet",
    "Rosaria": "flower plume goblet",
    "Escoffier": "sands goblet",
    "Emilie": "goblet",
    "Furina": "flower plume sands goblet circlet",
    "Bennett": "flower",
    "Kuki Shinobu": "sands",
    "Ororon": "circlet",
    "Yaoyao": "flower plume circlet",
    "Zhongli": "plume",
    "Xilonen": "plume",
    "Citlali": "flower plume sands goblet circlet",
}


def char_key(name: str) -> str:
    return name.replace(" ", "")


def main() -> None:
    if sys.argv[1:] not in (["--preview"], ["--commit"]):
        raise SystemExit("Use --preview or --commit")
    destination = Path(os.environ["LOCALAPPDATA"]) / "GenshinPlanner"
    database = destination / "app.db"
    os.environ.update({
        "GENSHIN_ENVIRONMENT": "desktop",
        "GENSHIN_DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "GENSHIN_SNAPSHOT_DIR": str(destination / "snapshots"),
        "GENSHIN_BACKUP_DIR": str(destination / "backups"),
        "GENSHIN_AKASHA_DIR": str(destination / "akasha"),
        "GENSHIN_LOG_DIR": str(destination / "logs"),
        "GENSHIN_GAME_DATA_PATH": str(destination / "game_data" / "game_data.json"),
    })

    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        source_rows = list(csv.DictReader(source))
    if len(source_rows) != 39 or len({row["name"] for row in source_rows}) != 39:
        raise RuntimeError("Akasha source must contain exactly 39 distinct builds")
    source_by_name = {row["name"]: row for row in source_rows}
    for row in source_rows:
        values = [int(row[slot]) for slot in SLOTS if row[slot]]
        if row["total"] and sum(values) != int(row["total"]):
            raise RuntimeError(f"Akasha RV total differs from slots: {row['name']}")

    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        snapshot_id = db.execute(
            "SELECT current_snapshot_id FROM accounts WHERE id='main'"
        ).fetchone()[0]
        if snapshot_id != EXPECTED_SNAPSHOT:
            raise RuntimeError(f"ProjectG snapshot changed: {snapshot_id}")
        effective_json = db.execute(
            "SELECT effective_state_json FROM snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()[0]
        effective = json.loads(effective_json)
        matched = []
        already_same = 0
        sample_before = []
        for name, slots_text in MATCHED.items():
            source = source_by_name[name]
            for slot in slots_text.split():
                if slot not in SLOTS or not source[slot]:
                    raise RuntimeError(f"Invalid Akasha slot: {name}/{slot}")
                rows = db.execute(
                    "SELECT artifact_instance_id, rv, rv_status FROM snapshot_artifacts "
                    "WHERE snapshot_id=? AND character_key=? AND slot_key=?",
                    (snapshot_id, char_key(name), slot),
                ).fetchall()
                if len(rows) != 1:
                    raise RuntimeError(f"Expected exactly one ProjectG artifact: {name}/{slot}")
                if rows[0][1] == int(source[slot]) and rows[0][2] == "IMPORTED":
                    already_same += 1
                if len(sample_before) < 5:
                    sample_before.append((name, slot, rows[0][1], rows[0][2], source[slot]))
                matched.append((name, slot, rows[0][0], int(source[slot])))

    matched_ids = {item[2] for item in matched}
    if len(matched_ids) != len(matched):
        raise RuntimeError("One ProjectG artifact matched multiple Akasha slots")
    rv_by_id = {artifact_id: rv for _, _, artifact_id, rv in matched}
    artifacts = []
    for index, item in enumerate(effective["artifacts"]):
        item = dict(item)
        source_id = item.get("id") or item.get("instanceId")
        artifact_id = source_id if isinstance(source_id, str) and source_id else f"artifact-{index}"
        if artifact_id in rv_by_id:
            item["rv"] = rv_by_id.pop(artifact_id)
        artifacts.append(item)
    if rv_by_id:
        raise RuntimeError(f"Matched artifacts absent from GOOD source: {sorted(rv_by_id)}")
    payload = {"format": "GOOD", "version": effective["version"],
               "dbVersion": effective.get("dbVersion", 1), "artifacts": artifacts}
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with REPORT.open("w", encoding="utf-8", newline="") as destination_file:
        writer = csv.writer(destination_file)
        writer.writerow(("character", "slot", "artifact_instance_id", "akasha_rv"))
        writer.writerows(matched)

    from projectg.bootstrap.dependencies import build_account_import_controller

    controller = build_account_import_controller()
    preview = controller.preview_good_file(str(PAYLOAD))
    print(json.dumps({"sourceBuilds": len(source_rows), "matchedPieces": len(matched),
                      "alreadySame": already_same,
                      "sampleBefore": sample_before,
                      "preview": preview}, ensure_ascii=True))
    if preview["duplicate"] or preview["abnormalChanges"]:
        raise RuntimeError("Preview rejected or flagged an abnormal change")
    if sys.argv[1] == "--commit":
        result = controller.commit_good_file(str(PAYLOAD))
        print(json.dumps({"commit": result}, ensure_ascii=True))


if __name__ == "__main__":
    main()
