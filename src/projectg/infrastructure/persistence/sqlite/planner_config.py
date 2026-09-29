"""SQLite persistence for versioned planner configuration."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projectg.domain.planning.config import (
    DEFAULT_PLANNER_CONFIG,
    PlannerConfig,
    config_from_payload,
    config_payload,
)
from projectg.infrastructure.persistence.sqlite.models import PlannerConfigVersion


def latest_config_row(db: Session):
    return db.scalar(select(PlannerConfigVersion).order_by(PlannerConfigVersion.version.desc()).limit(1))


def load_config(db: Session) -> PlannerConfig:
    row = latest_config_row(db)
    return config_from_payload(row.config_json, row.version) if row else DEFAULT_PLANNER_CONFIG


def save_config(db: Session, payload: dict) -> PlannerConfig:
    if latest_config_row(db) is None:
        db.add(PlannerConfigVersion(version=1, config_json=config_payload(DEFAULT_PLANNER_CONFIG)))
        db.flush()
    version = (db.scalar(select(func.max(PlannerConfigVersion.version))) or 0) + 1
    config = config_from_payload(payload, version)
    db.add(PlannerConfigVersion(version=version, config_json=config_payload(config)))
    db.flush()
    return config
