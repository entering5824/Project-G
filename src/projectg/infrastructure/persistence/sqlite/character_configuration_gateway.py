"""SQLite adapter for per-character planner configuration."""

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.character_configuration_gateway import (
    CharacterConfigurationContext,
    CharacterConfigurationData,
)
from projectg.domain.planning.tiers import LEGACY_DEFAULT_TIERS
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import (
    CharacterPriority,
    SnapshotCharacter,
    TierAssignmentVersion,
    TierConfigVersion,
)
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.repositories.targets import (
    active_preset_keys,
    presets_for_character,
)
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqliteCharacterConfigurationGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        mutation_uow: SqliteMutationUnitOfWork,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration
        self._mutations = mutation_uow

    def load_context(self, character_key: str) -> CharacterConfigurationContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = self._account(db)
                return self._context(db, account, character_key)

    def commit_validated(
        self,
        character_key: str,
        *,
        tier_key: str | None,
        priority_override: str,
    ) -> CharacterConfigurationData:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._account(db)
            context = self._context(db, account, character_key)
            if not context.owned:
                raise ValueError("Character is not owned in the current snapshot.")

            before_tier = context.data.tier_key
            before_priority = context.data.priority_override
            if before_tier == tier_key and before_priority == priority_override:
                return context.data

            effects.checkpoint("PRE_CHARACTER_CONFIG_CHANGE")
            if before_tier != tier_key:
                version = (
                    db.scalar(
                        select(func.max(TierAssignmentVersion.version)).where(
                            TierAssignmentVersion.account_id == account.id,
                            TierAssignmentVersion.character_key == character_key,
                        )
                    )
                    or 0
                ) + 1
                db.add(TierAssignmentVersion(
                    account_id=account.id,
                    character_key=character_key,
                    version=version,
                    tier_key=tier_key,
                ))
                effects.record_config_change(
                    account.id,
                    "TIER_CHANGED",
                    character_key,
                    before_tier,
                    tier_key,
                    character_key=character_key,
                    versions={
                        "previousTierVersion": context.data.tier_assignment_version or None,
                        "assignmentVersion": version,
                    },
                )

            if before_priority != priority_override:
                priority = db.get(CharacterPriority, (account.id, character_key))
                if priority is None:
                    db.add(CharacterPriority(
                        account_id=account.id,
                        character_key=character_key,
                        override=priority_override,
                    ))
                else:
                    priority.override = priority_override
                effects.record_config_change(
                    account.id,
                    "PRIORITY_OVERRIDE_CHANGED",
                    character_key,
                    before_priority,
                    priority_override,
                    character_key=character_key,
                )

            db.flush()
            return self._context(db, account, character_key).data

    def _account(self, db: Session):
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    @staticmethod
    def _tier_config(db: Session) -> tuple[int, list[dict]]:
        row = db.scalar(select(TierConfigVersion).order_by(TierConfigVersion.version.desc()).limit(1))
        if row:
            return row.version, row.tiers_json
        return 0, [dict(item) for item in LEGACY_DEFAULT_TIERS]

    @staticmethod
    def _latest_assignment(db: Session, account_id: str, character_key: str):
        return db.scalar(
            select(TierAssignmentVersion)
            .where(
                TierAssignmentVersion.account_id == account_id,
                TierAssignmentVersion.character_key == character_key,
            )
            .order_by(TierAssignmentVersion.version.desc())
            .limit(1)
        )

    def _context(self, db: Session, account, character_key: str) -> CharacterConfigurationContext:
        owned = bool(
            account.current_snapshot_id
            and db.get(SnapshotCharacter, (account.current_snapshot_id, character_key)) is not None
        )
        tier_version, tiers = self._tier_config(db)
        assignment = self._latest_assignment(db, account.id, character_key)
        priority = db.get(CharacterPriority, (account.id, character_key))
        active = active_preset_keys(db, account.id).get(character_key, "default")
        data = CharacterConfigurationData(
            character_key=character_key,
            tier_config_version=tier_version,
            tiers=tuple(tiers),
            tier_key=assignment.tier_key if assignment else None,
            tier_assignment_version=assignment.version if assignment else 0,
            priority_override=priority.override if priority else "NORMAL",
            active_preset_key=active,
            presets=tuple(presets_for_character(db, account.id, character_key)),
        )
        return CharacterConfigurationContext(owned=owned, data=data)
