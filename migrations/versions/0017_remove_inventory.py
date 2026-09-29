"""Remove persistent material inventory and inventory-dependent planner state."""
import json
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "0017_remove_inventory"
down_revision = "0016_primary_planner_team"
branch_labels = None
depends_on = None


def _strip_inventory(value):
    if isinstance(value, dict):
        for key in list(value):
            if key in {"materials", "inventory", "inventoryVersion", "inventoryKnown",
                       "inventoryState", "inventoryReserves", "owned", "reserved",
                       "available", "allocated", "craftable", "expRecommendation"}:
                value.pop(key, None)
            else:
                _strip_inventory(value[key])
    elif isinstance(value, list):
        for item in value:
            _strip_inventory(item)


def _sanitize_file(raw_path):
    if not raw_path:
        return
    path = Path(raw_path)
    if not path.is_file():
        return
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or "materials" not in payload:
            return
        payload.pop("materials", None)
        temporary = path.with_name(path.name + ".inventory-removal.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        # The retained pre-migration automatic backup is the recovery source.
        raise RuntimeError(f"Could not remove material inventory from snapshot file: {path}")


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "history_events" in tables:
        bind.execute(sa.text("DELETE FROM history_events WHERE event_type = 'MATERIAL_QUANTITY_CHANGED'"))
    if "snapshots" in tables:
        rows = bind.execute(sa.text("SELECT id, raw_path, effective_state_json, coverage_json FROM snapshots")).mappings()
        for row in rows:
            _sanitize_file(row["raw_path"])
            effective = row["effective_state_json"]
            coverage = row["coverage_json"]
            if isinstance(effective, str):
                effective = json.loads(effective)
            if isinstance(coverage, str):
                coverage = json.loads(coverage)
            _strip_inventory(effective)
            if isinstance(coverage, dict):
                coverage.pop("materials", None)
            bind.execute(sa.text("UPDATE snapshots SET effective_state_json=:state, coverage_json=:coverage WHERE id=:id"),
                {"state": json.dumps(effective), "coverage": json.dumps(coverage), "id": row["id"]})
    if "plan_runs" in tables:
        columns = {column["name"] for column in sa.inspect(bind).get_columns("plan_runs")}
        for row in bind.execute(sa.text("SELECT id, normalized_input_json, result_json FROM plan_runs")).mappings():
            normalized, result = row["normalized_input_json"], row["result_json"]
            if isinstance(normalized, str):
                normalized = json.loads(normalized)
            if isinstance(result, str):
                result = json.loads(result)
            _strip_inventory(normalized)
            _strip_inventory(result)
            bind.execute(sa.text("UPDATE plan_runs SET normalized_input_json=:normalized, result_json=:result WHERE id=:id"),
                         {"normalized": json.dumps(normalized), "result": json.dumps(result), "id": row["id"]})
        if "inventory_version" in columns:
            with op.batch_alter_table("plan_runs") as batch:
                batch.drop_column("inventory_version")
    for table in ("snapshot_material_inventory", "inventory_reserves", "inventory_entries",
                  "inventory_state"):
        if table in tables:
            op.drop_table(table)


def downgrade():
    raise RuntimeError("Inventory removal is irreversible; restore a pre-migration backup to recover old data.")
