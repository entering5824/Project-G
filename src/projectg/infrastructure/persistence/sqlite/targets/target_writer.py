"""Versioned target-row writes isolated from target workflow orchestration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import Account, CharacterTargetPreset, CharacterTargetVersion
from projectg.infrastructure.persistence.sqlite.repositories.targets import active_preset_keys, latest_active_targets


@dataclass(frozen=True)
class TargetWriteBatch:
    saved: list[dict]
    before: dict[str, CharacterTargetVersion]
    after: dict[str, CharacterTargetVersion]


class TargetWriter:
    @staticmethod
    def next_version(db: Session, account_id: str, character_key: str) -> int:
        return (
            db.scalar(
                select(func.max(CharacterTargetVersion.version)).where(
                    CharacterTargetVersion.account_id == account_id,
                    CharacterTargetVersion.character_key == character_key,
                )
            )
            or 0
        ) + 1

    def save_many(
        self,
        db: Session,
        account: Account,
        selected_targets: dict[str, dict],
    ) -> TargetWriteBatch:
        before = latest_active_targets(db, account.id)
        saved = [
            self.save_one(db, account, key, selected_targets[key])
            for key in sorted(selected_targets)
        ]
        db.flush()
        return TargetWriteBatch(
            saved=saved,
            before=before,
            after=latest_active_targets(db, account.id),
        )

    def save_one(self, db: Session, account: Account, character_key: str, target: dict) -> dict:
        preset_key = active_preset_keys(db, account.id).get(character_key, "default")
        preset = db.get(CharacterTargetPreset, (account.id, character_key, preset_key))
        if preset is None:
            preset_key = "default"
            db.add(
                CharacterTargetPreset(
                    account_id=account.id,
                    character_key=character_key,
                    preset_key=preset_key,
                    label="Default",
                    is_active=True,
                )
            )
        version = self.next_version(db, account.id, character_key)
        db.add(
            CharacterTargetVersion(
                account_id=account.id,
                character_key=character_key,
                preset_key=preset_key,
                version=version,
                target_json=deepcopy(target),
            )
        )
        return {
            "characterKey": character_key,
            "configured": True,
            "version": version,
            "target": deepcopy(target),
        }
