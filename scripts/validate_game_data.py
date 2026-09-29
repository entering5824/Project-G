"""Validate the committed local GameData JSON without network access."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from projectg.infrastructure.game_data.json.loader import DATASET, load_game_data
from projectg.application.game_data.policy import catalog_coverage


if __name__ == "__main__":
    game = load_game_data(DATASET, strict=True)
    print({"metadata": game.metadata, "coverage": catalog_coverage(game)})
