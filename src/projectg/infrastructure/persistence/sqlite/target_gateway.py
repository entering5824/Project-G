"""SQLite adapter for versioned character-target workflows."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.target_gateway import (
    TargetGateway,
    TargetImportContext,
    TargetOperationResult,
    TargetPresetContext,
)
from projectg.application.targets.errors import TargetOperationError
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.targets import (
    TargetContextReader,
    TargetIdempotencyRepository,
    TargetPresetRepository,
    TargetWriter,
)


class SqliteTargetGateway(TargetGateway):
    """Application-port facade over small SQLite target persistence primitives."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        game_data_provider: Callable,
        mutation_uow: SqliteMutationUnitOfWork,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._mutations = mutation_uow
        self._context = TargetContextReader(configuration, game_data_provider)
        self._idempotency = TargetIdempotencyRepository()
        self._writer = TargetWriter()
        self._presets = TargetPresetRepository(self._writer)

    def import_context(self) -> TargetImportContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                return self._context.import_context(db)

    def preset_context(self, character_key: str) -> TargetPresetContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                return self._context.preset_context(db, character_key)

    def commit_validated(
        self,
        *,
        payload: object,
        selected_targets: dict[str, dict],
        operation_id: str,
        preview: dict,
    ) -> TargetOperationResult:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._context.account(db)
            if not account.current_snapshot_id:
                raise TargetOperationError(
                    "ACCOUNT_NOT_IMPORTED", "Import a GOOD snapshot before targets.", {}
                )

            selected = set(selected_targets)
            payload_hash = self._idempotency.fingerprint(payload, selected)
            prior = self._idempotency.get(db, account.id, operation_id)
            if prior is not None:
                if prior.payload_hash != payload_hash:
                    raise TargetOperationError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "This import key was already used for a different request.",
                        {},
                        status_code=409,
                    )
                return TargetOperationResult(self._idempotency.response(prior))

            effects.checkpoint("PRE_TARGET_IMPORT")
            batch = self._writer.save_many(db, account, selected_targets)
            for key in sorted(selected):
                old, current = batch.before.get(key), batch.after[key]
                effects.record_config_change(
                    account.id,
                    "TARGET_CHANGED",
                    key,
                    old.target_json if old else None,
                    current.target_json,
                    character_key=key,
                    versions={
                        "previousTargetVersion": old.version if old else None,
                        "targetVersion": current.version,
                    },
                )

            effects.reconcile_completion(
                account,
                account.current_snapshot_id,
                account.current_snapshot_id,
                reason="TARGET_CHANGED",
                before_targets=self._target_versions(batch.before),
                after_targets=self._target_versions(batch.after),
            )
            response = {
                "mode": "MERGE",
                "saved": batch.saved,
                "unknownCharacters": preview["unknownCharacters"],
                "invalidTargets": preview["invalidTargets"],
            }
            self._idempotency.store(
                db,
                account_id=account.id,
                operation_id=operation_id,
                payload_hash=payload_hash,
                response=response,
            )
            return TargetOperationResult(response)

    def create_preset(
        self,
        *,
        character_key: str,
        preset_key: str,
        label: str,
        cloned_target: dict,
        cloned_from_preset: str,
    ) -> TargetOperationResult:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._context.account(db)
            if self._presets.exists(db, account.id, character_key, preset_key):
                raise TargetOperationError(
                    "TARGET_PRESET_CONFLICT",
                    "Target preset key already exists.",
                    {"characterKey": character_key, "presetKey": preset_key},
                    status_code=409,
                )

            effects.checkpoint("PRE_TARGET_PRESET_CREATE")
            created = self._presets.create(
                db,
                account,
                character_key=character_key,
                preset_key=preset_key,
                label=label,
                cloned_target=cloned_target,
            )
            effects.record_config_change(
                account.id,
                "TARGET_PRESET_CREATED",
                f"{character_key}:{preset_key}",
                None,
                {
                    "characterKey": character_key,
                    "presetKey": preset_key,
                    "label": label,
                    "clonedFromPreset": cloned_from_preset,
                },
                character_key=character_key,
                versions={"targetVersion": created.version},
            )
            return TargetOperationResult(created.response)

    def activate_preset(self, character_key: str, preset_key: str) -> TargetOperationResult:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._context.account(db)
            plan = self._presets.prepare_activation(db, account, character_key, preset_key)
            if plan is None:
                raise TargetOperationError(
                    "TARGET_PRESET_NOT_FOUND",
                    "Target preset was not found.",
                    {"characterKey": character_key, "presetKey": preset_key},
                    status_code=404,
                )
            if plan.changed:
                effects.checkpoint("PRE_TARGET_PRESET_ACTIVATE")
            activation = self._presets.activate(db, account, character_key, preset_key, plan)
            if not activation.changed:
                return TargetOperationResult(activation.response)

            old_row = activation.before_targets.get(character_key)
            new_row = activation.after_targets.get(character_key)
            effects.record_config_change(
                account.id,
                "TARGET_PRESET_ACTIVATED",
                character_key,
                {
                    "presetKey": activation.before_active_key,
                    "target": old_row.target_json if old_row else None,
                },
                {
                    "presetKey": preset_key,
                    "target": new_row.target_json if new_row else None,
                },
                character_key=character_key,
                versions={"targetVersion": new_row.version if new_row else None},
            )
            effects.reconcile_completion(
                account,
                account.current_snapshot_id,
                account.current_snapshot_id,
                reason="TARGET_PRESET_ACTIVATED",
                before_targets=self._target_versions(activation.before_targets),
                after_targets=self._target_versions(activation.after_targets),
            )
            return TargetOperationResult(activation.response)

    @staticmethod
    def _target_versions(rows: dict) -> dict[str, tuple[int, dict]]:
        return {key: (row.version, row.target_json) for key, row in rows.items()}
