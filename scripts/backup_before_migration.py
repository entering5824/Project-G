"""Create a conservative pre-migration copy of legacy local data."""
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from projectg.bootstrap.settings import settings


def main():
    url=settings.database_url
    if not url.startswith("sqlite:///") or url=="sqlite:///:memory:":
        raise SystemExit("Pre-migration backup supports file-based SQLite only.")
    database=Path(url.removeprefix("sqlite:///"))
    if not database.exists():
        print("No existing database; skipping pre-migration backup.")
        return
    settings.backup_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target=settings.backup_dir/f"pre_migration_{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="planner-pre-migration-") as temporary:
        temporary=Path(temporary)
        database_copy=temporary/"database.sqlite"
        source=sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro",uri=True)
        destination=sqlite3.connect(database_copy)
        source.backup(destination)
        destination.close();source.close()
        snapshots=sorted(path for path in settings.snapshot_dir.rglob("*") if path.is_file()) if settings.snapshot_dir.exists() else []
        manifest={"backupSchemaVersion":1,"kind":"PRE_MIGRATION","exportedAt":datetime.now(timezone.utc).isoformat(),
                  "includesAkashaImages":False,"snapshotFileCount":len(snapshots)}
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
            archive.write(database_copy,"database.sqlite")
            archive.writestr("manifest.json",json.dumps(manifest,indent=2))
            for path in snapshots:
                archive.write(path,f"snapshots/{path.relative_to(settings.snapshot_dir).as_posix()}")
    print(f"Pre-migration backup created: {target}")


if __name__=="__main__":
    main()
