"""Target version and preset queries for SQLite persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import CharacterTargetPreset, CharacterTargetVersion


def active_preset_keys(db: Session, account_id: str) -> dict[str, str]:
    rows = db.scalars(select(CharacterTargetPreset).where(
        CharacterTargetPreset.account_id == account_id,
        CharacterTargetPreset.is_active.is_(True),
    ).order_by(CharacterTargetPreset.character_key, CharacterTargetPreset.preset_key)).all()
    return {row.character_key: row.preset_key for row in rows}


def latest_target_for_preset(db: Session, account_id: str, character_key: str,
                             preset_key: str) -> CharacterTargetVersion | None:
    return db.scalar(select(CharacterTargetVersion).where(
        CharacterTargetVersion.account_id == account_id,
        CharacterTargetVersion.character_key == character_key,
        CharacterTargetVersion.preset_key == preset_key,
    ).order_by(CharacterTargetVersion.version.desc()).limit(1))


def latest_active_targets(db: Session, account_id: str) -> dict[str, CharacterTargetVersion]:
    active = active_preset_keys(db, account_id)
    rows = db.scalars(select(CharacterTargetVersion).where(
        CharacterTargetVersion.account_id == account_id,
    ).order_by(CharacterTargetVersion.character_key, CharacterTargetVersion.version.desc())).all()
    result: dict[str, CharacterTargetVersion] = {}
    for row in rows:
        if row.preset_key == active.get(row.character_key, "default"):
            result.setdefault(row.character_key, row)
    return result


def presets_for_character(db: Session, account_id: str, character_key: str) -> list[dict]:
    active = active_preset_keys(db, account_id).get(character_key, "default")
    rows = db.scalars(select(CharacterTargetPreset).where(
        CharacterTargetPreset.account_id == account_id,
        CharacterTargetPreset.character_key == character_key,
    ).order_by(CharacterTargetPreset.created_at, CharacterTargetPreset.preset_key)).all()
    return [{"key": row.preset_key, "label": row.label, "active": row.preset_key == active}
            for row in rows]
