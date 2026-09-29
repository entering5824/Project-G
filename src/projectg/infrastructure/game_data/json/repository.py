from functools import lru_cache
from pathlib import Path
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.game_data.json.loader import dataset_path, load_game_data
from projectg.domain.game_catalog.models import GameData


@lru_cache(maxsize=4)
def _load_game_data_version(path: str, modified_ns: int, size: int) -> GameData:
    # Include the on-disk version in the cache key so a replaced local dataset
    # is picked up on the next request without a process restart.
    return load_game_data(Path(path))


def get_game_data(configuration: Settings) -> GameData:
    path = dataset_path(configuration)
    try:
        stat = path.stat()
    except OSError:
        return load_game_data(path)
    return _load_game_data_version(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
