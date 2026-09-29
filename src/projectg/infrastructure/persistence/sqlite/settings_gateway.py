"""SQLite adapter for persisted application settings."""

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from projectg.application.ports.outbound.settings_gateway import SettingsData
from projectg.domain.planning.config import config_payload
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.artifacts.service import (
    load_quality_config,
    save_quality_config,
)
from projectg.infrastructure.persistence.sqlite.planner_config import (
    latest_config_row,
    load_config,
    save_config,
)
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.infrastructure.persistence.sqlite.repositories.targets import latest_active_targets
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqliteSettingsGateway:
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

    def load(self) -> SettingsData:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = self._account(db)
                return self._data(db, account)

    def commit_validated(
        self,
        planner: dict[str, Any],
        artifact: dict[str, Any],
        account: dict[str, Any] | None,
    ) -> SettingsData:
        with self._mutations.transaction() as effects:
            db = effects.db
            account_row = self._account(db)
            if db.get(type(account_row), account_row.id) is None:
                db.add(account_row)
                db.flush()

            previous_row = latest_config_row(db)
            previous_planner = config_payload(load_config(db))
            before_quality = load_quality_config(db)
            before_artifact = before_quality.to_dict()
            before_account = self._account_payload(account_row)
            artifact_payload = {
                "adapterType": before_quality.adapter_type,
                "thresholds": before_quality.thresholds,
            }
            changed = (
                planner != previous_planner
                or artifact != artifact_payload
                or (account is not None and account != before_account)
            )
            if not changed:
                return self._data(db, account_row)

            effects.checkpoint("PRE_SETTINGS_CHANGE")
            planner_config = load_config(db)
            quality = before_quality
            if planner != previous_planner:
                planner_config = save_config(db, planner)
                current = config_payload(planner_config)
                effects.record_config_change(
                    account_row.id,
                    "PLANNER_CONFIG_CHANGED",
                    "planner",
                    previous_planner,
                    current,
                    versions={
                        "previousPlannerConfigVersion": previous_row.version if previous_row else 0,
                        "plannerConfigVersion": int(planner_config.config_version),
                    },
                )

            if artifact != artifact_payload:
                quality = save_quality_config(db, artifact)
                effects.record_config_change(
                    account_row.id,
                    "ARTIFACT_QUALITY_CONFIG_CHANGED",
                    "artifactQuality",
                    before_artifact,
                    quality.to_dict(),
                    versions={"newArtifactQualityConfigVersion": quality.version},
                )
                targets = latest_active_targets(db, account_row.id)
                versions = {
                    key: (row.version, row.target_json)
                    for key, row in targets.items()
                }
                effects.reconcile_completion(
                    account_row,
                    account_row.current_snapshot_id,
                    account_row.current_snapshot_id,
                    reason="ARTIFACT_QUALITY_CONFIG_CHANGED",
                    before_targets=versions,
                    after_targets=versions,
                    before_quality_config=before_quality,
                    after_quality_config=quality,
                )

            if account is not None and account != before_account:
                account_row.server_region = account["serverRegion"]
                account_row.game_language = account["gameLanguage"]
                account_row.world_level = account["worldLevel"]
                account_row.resin = account["resin"]
                account_row.weekly_claimed_json = account["weeklyClaimed"]
                account_row.unavailable_sources_json = account["unavailableSources"]
                effects.record_config_change(
                    account_row.id,
                    "ACCOUNT_SETTINGS_CHANGED",
                    "accountSettings",
                    before_account,
                    account,
                )

            db.flush()
            return self._data(db, account_row)

    def _account(self, db: Session):
        return AccountRepository().get_or_create(
            db,
            self._configuration.account_id,
            self._configuration.account_name,
            self._configuration.server_region,
        )

    @classmethod
    def _data(cls, db: Session, account) -> SettingsData:
        planner = load_config(db)
        quality = load_quality_config(db)
        return SettingsData(
            planner=config_payload(planner),
            planner_version=int(planner.config_version),
            artifact=quality.to_dict(),
            artifact_configured=quality.configured,
            account=cls._account_payload(account),
        )

    @staticmethod
    def _account_payload(account) -> dict[str, Any]:
        return {
            "serverRegion": account.server_region,
            "gameLanguage": account.game_language,
            "worldLevel": account.world_level,
            "resin": account.resin,
            "weeklyClaimed": account.weekly_claimed_json or [],
            "unavailableSources": account.unavailable_sources_json or [],
        }
