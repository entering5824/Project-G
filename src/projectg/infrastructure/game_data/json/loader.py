import json
import sys
from pathlib import Path
from typing import Any

from projectg.infrastructure.configuration.settings import Settings
from projectg.domain.game_catalog.models import GameData
from projectg.infrastructure.game_data.json.normalization import normalize_game_data
from projectg.domain.game_catalog.validation import validate_game_data

# Reference path for tests and build tooling; runtime configuration supplies
# the active catalog path.
if hasattr(sys, "_MEIPASS"):
    DATASET = Path(sys._MEIPASS) / "data" / "static" / "genshin-impact" / "game_data.json"
else:
    DATASET = Path(__file__).resolve().parents[5] / "data" / "static" / "genshin-impact" / "game_data.json"


def dataset_path(configuration: Settings) -> Path:
    return Path(configuration.game_data_path)


def load_raw(path: Path) -> dict[str, Any]:
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_game_data(path: Path, *, strict: bool = False) -> GameData:
    try:
        raw = load_raw(path)
        # JSON arrays are checked before dict construction to avoid silent duplicate-key overwrites.
        for name in ("characters", "weapons", "materials", "domains", "bosses", "artifact_sets"):
            keys = [row.get("key") for row in raw.get(name, [])]
            duplicates = sorted(key for key, count in __import__("collections").Counter(keys).items() if count > 1)
            if duplicates:
                raise ValueError(f"Duplicate {name} keys: {duplicates}")
        data = normalize_game_data(raw)
        validate_game_data(data)
        return data
    except Exception as exc:
        if strict:
            raise
        return GameData(metadata={}, error={"code": "GAMEDATA_INVALID", "message": str(exc),
            "details": getattr(exc, "problems", [])})
