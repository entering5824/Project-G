"""Runtime configuration loaded from the process environment."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ROOT = PROJECT_ROOT / "data" / "runtime"


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = f"sqlite:///{(ROOT / 'app.db').as_posix()}"
    snapshot_dir: Path = ROOT / "snapshots"
    backup_dir: Path = ROOT / "backups"
    akasha_dir: Path = ROOT / "akasha"
    log_dir: Path = ROOT / "logs"
    game_data_path: Path = PROJECT_ROOT / "data" / "static" / "genshin-impact" / "game_data.json"
    build_profiles_path: Path = PROJECT_ROOT / "data" / "static" / "builds" / "build_profiles.json"
    account_id: str = "main"
    account_name: str = "Main Account"
    server_region: str = "ASIA"

    model_config = SettingsConfigDict(env_prefix="GENSHIN_", extra="ignore")


settings = Settings()
