"""SQLite adapter for the user's saved tier pack."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.tier_pack_gateway import TierPackContext
from projectg.domain.planning.tier_pack import tier_pack_content
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.game_data.json.build_profiles import load_build_pack
from projectg.infrastructure.persistence.sqlite.models import SnapshotCharacter
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.repositories.tier_pack import (
    append_tier_pack_version,
    current_tier_pack,
)
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.serialization.tier_pack_digest import tier_pack_hash


class SqliteTierPackGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        game_data,
        mutation_uow: SqliteMutationUnitOfWork,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration
        self._game_data = game_data
        self._mutations = mutation_uow

    def load_context(self) -> TierPackContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = self._account(db)
                return self._context(db, account)

    def commit_validated(self, payload: dict) -> dict:
        with self._mutations.transaction() as effects:
            db = effects.db
            account = self._account(db)
            previous = current_tier_pack(db, account.id)
            if tier_pack_content(previous) == payload:
                return previous

            effects.checkpoint("PRE_TIER_PACK_CHANGE")
            version = int(previous["packVersion"]) + 1
            append_tier_pack_version(
                db,
                account.id,
                version=version,
                payload=payload,
            )
            return {**payload, "packVersion": version}

    def _account(self, db: Session):
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    def _context(self, db: Session, account) -> TierPackContext:
        pack = current_tier_pack(db, account.id)
        owned: set[str] = set()
        if account.current_snapshot_id:
            owned = set(db.scalars(
                select(SnapshotCharacter.character_key).where(
                    SnapshotCharacter.snapshot_id == account.current_snapshot_id
                )
            ).all())

        character_keys = frozenset(self._game_data.characters)
        knowledge = load_build_pack(
            self._configuration.build_profiles_path,
            character_keys=set(character_keys),
        )
        set_options: dict[str, tuple[str, ...]] = {}
        for key in character_keys:
            values = {
                set_key
                for profile in knowledge.profiles.get(key, [])
                for option in profile.get("artifacts", {}).get("setOptions", [])
                for set_key in [option.get("setKey")]
                if set_key
            }
            values.update({
                part.get("setKey")
                for profile in knowledge.profiles.get(key, [])
                for option in profile.get("artifacts", {}).get("setCombinations", [])
                for part in option.get("combination", [])
                if part.get("setKey")
            })
            set_options[key] = tuple(sorted(values))

        return TierPackContext(
            pack=pack,
            pack_hash=tier_pack_hash(pack),
            owned_characters=frozenset(owned),
            character_keys=character_keys,
            artifact_set_keys=frozenset(self._game_data.artifact_sets),
            set_options=set_options,
        )
