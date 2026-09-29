"""Read persisted planner and artifact quality configuration."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from projectg.infrastructure.persistence.sqlite.models import CharacterPriority, AccountPlanningIntent
from projectg.domain.planning.config import PlannerConfig
from projectg.domain.artifacts.models import ArtifactQualityConfig
from projectg.infrastructure.persistence.sqlite.planner_config import load_config
from projectg.infrastructure.persistence.sqlite.artifacts.service import load_quality_config


class PlannerConfigurationReader:
    def __init__(self, db: Session):
        self._db = db

    def read_planner(self) -> PlannerConfig:
        return load_config(self._db)

    def read_artifact_quality(self) -> ArtifactQualityConfig:
        return load_quality_config(self._db)

    def read_priorities(self, account_id: str) -> dict[str, str]:
        return {row.character_key: row.override for row in self._db.scalars(
            select(CharacterPriority).where(CharacterPriority.account_id == account_id)
        )}

    def read_build_intents(self, account_id: str) -> tuple[dict[str, str], dict]:
        row = self._db.get(AccountPlanningIntent, account_id)
        if row is None:
            return {}, {}
        return dict(row.personal_json or {}), dict(row.theater_json or {})

    def read_personal_priority_keys(self, account_id: str) -> set[str]:
        personal, _ = self.read_build_intents(account_id)
        return {key for key, state in personal.items() if state == "WANT_BUILD"}
