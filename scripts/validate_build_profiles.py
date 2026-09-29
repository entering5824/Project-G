"""Validate local Build Knowledge coverage and report the release gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from projectg.bootstrap.settings import settings
from projectg.infrastructure.game_data.json.build_profiles import load_build_pack
from projectg.infrastructure.game_data.json.loader import DATASET, load_raw


def main() -> int:
    keys = {row["key"] for row in load_raw(DATASET)["characters"]}
    pack = load_build_pack(settings.build_profiles_path, character_keys=keys)
    report = {
        "packVersion": pack.version,
        "gameVersion": pack.game_version,
        "coverage": pack.coverage,
        "errors": list(pack.errors),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if pack.coverage.get("releaseReady") and not pack.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
