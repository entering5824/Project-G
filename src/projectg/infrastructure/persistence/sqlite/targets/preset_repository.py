"""SQLite persistence primitives for named target presets."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import Account, CharacterTargetPreset, CharacterTargetVersion
from projectg.infrastructure.persistence.sqlite.repositories.targets import (
    active_preset_keys,
    latest_active_targets,
    latest_target_for_preset,
    presets_for_character,
)
from projectg.infrastructure.persistence.sqlite.targets.target_writer import TargetWriter


@dataclass(frozen=True)
class PresetCreation:
    version: int
    response: dict


@dataclass(frozen=True)
class PresetActivationPlan:
    before_active_key: str
    before_targets: dict[str, CharacterTargetVersion]
    selected_preset: CharacterTargetPreset
    selected_target: CharacterTargetVersion
    changed: bool


@dataclass(frozen=True)
class PresetActivation:
    before_active_key: str
    before_targets: dict[str, CharacterTargetVersion]
    after_targets: dict[str, CharacterTargetVersion]
    response: dict
    changed: bool


class TargetPresetRepository:
    def __init__(self, writer: TargetWriter):
        self._writer = writer

    @staticmethod
    def exists(db: Session, account_id: str, character_key: str, preset_key: str) -> bool:
        return db.get(CharacterTargetPreset, (account_id, character_key, preset_key)) is not None

    def create(
        self,
        db: Session,
        account: Account,
        *,
        character_key: str,
        preset_key: str,
        label: str,
        cloned_target: dict,
    ) -> PresetCreation:
        version = self._writer.next_version(db, account.id, character_key)
        db.add(
            CharacterTargetPreset(
                account_id=account.id,
                character_key=character_key,
                preset_key=preset_key,
                label=label,
                is_active=False,
            )
        )
        db.add(
            CharacterTargetVersion(
                account_id=account.id,
                character_key=character_key,
                preset_key=preset_key,
                version=version,
                target_json=deepcopy(cloned_target),
            )
        )
        db.flush()
        return PresetCreation(
            version=version,
            response={
                "characterKey": character_key,
                "presetKey": preset_key,
                "label": label,
                "active": False,
                "version": version,
                "target": deepcopy(cloned_target),
                "presets": presets_for_character(db, account.id, character_key),
            },
        )

    @staticmethod
    def prepare_activation(
        db: Session,
        account: Account,
        character_key: str,
        preset_key: str,
    ) -> PresetActivationPlan | None:
        selected = db.get(CharacterTargetPreset, (account.id, character_key, preset_key))
        row = latest_target_for_preset(db, account.id, character_key, preset_key)
        if selected is None or row is None:
            return None
        before_targets = latest_active_targets(db, account.id)
        before_active = active_preset_keys(db, account.id).get(character_key, "default")
        return PresetActivationPlan(
            before_active_key=before_active,
            before_targets=before_targets,
            selected_preset=selected,
            selected_target=row,
            changed=before_active != preset_key,
        )

    @staticmethod
    def activate(
        db: Session,
        account: Account,
        character_key: str,
        preset_key: str,
        plan: PresetActivationPlan,
    ) -> PresetActivation:
        if plan.changed:
            preset_rows = db.scalars(
                select(CharacterTargetPreset).where(
                    CharacterTargetPreset.account_id == account.id,
                    CharacterTargetPreset.character_key == character_key,
                )
            ).all()
            for item in preset_rows:
                item.is_active = False
            db.flush()
            plan.selected_preset.is_active = True
            db.flush()
            after_targets = latest_active_targets(db, account.id)
        else:
            after_targets = plan.before_targets

        return PresetActivation(
            before_active_key=plan.before_active_key,
            before_targets=plan.before_targets,
            after_targets=after_targets,
            changed=plan.changed,
            response={
                "characterKey": character_key,
                "presetKey": preset_key,
                "version": plan.selected_target.version,
                "target": deepcopy(plan.selected_target.target_json),
                "presets": presets_for_character(db, account.id, character_key),
            },
        )
