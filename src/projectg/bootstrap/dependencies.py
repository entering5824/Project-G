"""Composition helpers for wiring application ports to concrete adapters."""

from projectg.application.use_cases.imports.commit_account_import import CommitAccountImport
from projectg.application.use_cases.imports.commit_good_file import CommitGoodFile
from projectg.application.use_cases.imports.preview_account_import import PreviewAccountImport
from projectg.application.use_cases.imports.preview_good_file import PreviewGoodFile
from projectg.infrastructure.filesystem.local_file_storage import LocalFileStorage
from projectg.infrastructure.configuration.settings import settings
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.clock.game_clock import GameClock
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
from projectg.infrastructure.serialization.good_importer import GoodImporter
from projectg.infrastructure.serialization.good_document import GoodDocumentParser
from projectg.infrastructure.serialization.target_document_source import JsonTargetDocumentSource
from projectg.infrastructure.serialization.aef_exchange import AefArtifactDocumentParser
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import_gateway import SqliteAccountImportGateway
from projectg.infrastructure.persistence.sqlite.session import create_database_runtime
from projectg.application.use_cases.settings.get_settings import GetSettings
from projectg.application.use_cases.settings.save_settings import SaveSettings
from projectg.infrastructure.persistence.sqlite.settings_gateway import SqliteSettingsGateway
from projectg.application.use_cases.teams.get_teams import GetTeams
from projectg.application.use_cases.teams.save_teams import SaveTeams
from projectg.infrastructure.persistence.sqlite.teams_gateway import SqliteTeamsGateway
from projectg.application.use_cases.characters.get_configuration import GetCharacterConfiguration
from projectg.application.use_cases.characters.save_configuration import SaveCharacterConfiguration
from projectg.infrastructure.persistence.sqlite.character_configuration_gateway import SqliteCharacterConfigurationGateway
from projectg.interface_adapters.controllers.account_import_controller import AccountImportController
from projectg.interface_adapters.controllers.settings_controller import SettingsController
from projectg.interface_adapters.controllers.teams_controller import TeamsController
from projectg.interface_adapters.controllers.character_configuration_controller import CharacterConfigurationController
from projectg.application.use_cases.game_data.export_pack import ExportGameDataPack
from projectg.application.use_cases.game_data.get_installed_status import GetInstalledGameDataStatus
from projectg.application.use_cases.game_data.install_pack import InstallGameDataPack
from projectg.application.use_cases.game_data.preview_pack import PreviewGameDataPack
from projectg.infrastructure.game_data.json.pack_storage import LocalGameDataPackStorage
from projectg.infrastructure.persistence.sqlite.game_data_account_gateway import SqliteGameDataAccountGateway
from projectg.interface_adapters.controllers.game_data_controller import GameDataController
from projectg.application.use_cases.artifacts.confirm_exchange import ConfirmArtifactExchange
from projectg.application.use_cases.artifacts.preview_exchange import PreviewArtifactExchange
from projectg.infrastructure.persistence.sqlite.artifact_exchange_gateway import SqliteArtifactExchangeGateway
from projectg.interface_adapters.controllers.artifact_exchange_controller import ArtifactExchangeController
from projectg.application.use_cases.planner_state.preview_pin import PreviewPin
from projectg.application.use_cases.planner_state.set_pin import SetPin
from projectg.application.use_cases.planner_state.list_plan_runs import ListPlanRuns
from projectg.application.use_cases.planner_state.replay_plan_run import ReplayPlanRun
from projectg.infrastructure.persistence.sqlite.planner_state_gateway import SqlitePlannerStateGateway
from projectg.interface_adapters.controllers.planner_state_controller import PlannerStateController
from projectg.application.use_cases.targets.activate_target_preset import ActivateTargetPreset
from projectg.application.use_cases.targets.commit_targets import CommitTargets
from projectg.application.use_cases.targets.create_target_preset import CreateTargetPreset
from projectg.application.use_cases.targets.preview_target_file import PreviewTargetFile
from projectg.application.use_cases.targets.preview_target_payload import PreviewTargetPayload
from projectg.infrastructure.persistence.sqlite.target_gateway import SqliteTargetGateway
from projectg.interface_adapters.controllers.target_controller import TargetController
from projectg.application.use_cases.tier_packs.get_tier_pack import GetTierPack
from projectg.application.use_cases.tier_packs.save_tier_pack import SaveTierPack
from projectg.application.use_cases.tier_packs.validate_tier_pack import ValidateTierPack
from projectg.infrastructure.persistence.sqlite.tier_pack_gateway import SqliteTierPackGateway
from projectg.infrastructure.filesystem.local_file_storage import LocalFileStorage
from projectg.interface_adapters.controllers.tier_pack_controller import TierPackController
from projectg.application.use_cases.support.compare_history import CompareHistory
from projectg.application.use_cases.backups.create_backup import CreateBackup
from projectg.application.use_cases.support.get_data_health import GetDataHealth
from projectg.application.use_cases.support.get_history import GetHistory
from projectg.application.use_cases.support.get_logs_directory import GetLogsDirectory
from projectg.application.use_cases.backups.restore_backup import RestoreBackup
from projectg.infrastructure.persistence.sqlite.support_gateway import SqliteSupportGateway
from projectg.interface_adapters.controllers.support_controller import SupportController
from projectg.application.use_cases.overview.get_overview import GetOverview
from projectg.infrastructure.persistence.sqlite.overview_gateway import SqliteOverviewGateway
from projectg.infrastructure.persistence.sqlite.today_planner import TodayPlanner
from projectg.application.use_cases.planning.run_planner import RunPlanner
from projectg.infrastructure.persistence.sqlite.planner_gateway import SqlitePlannerGateway
from projectg.infrastructure.game_data.json.catalog_gateway import LocalGameDataGateway
from projectg.infrastructure.game_data.json.build_knowledge_gateway import LocalBuildKnowledgeGateway
from projectg.infrastructure.persistence.sqlite.data_health_gateway import SqliteDataHealthFactsGateway
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.persistence.sqlite.build_intent_gateway import SqliteBuildIntentGateway
from projectg.interface_adapters.controllers.build_intent_controller import BuildIntentController
from projectg.infrastructure.backups.local_backup_gateway import LocalBackupGateway
from projectg.infrastructure.game_data.json.build_profiles import load_build_pack

_database_runtime = create_database_runtime(settings.database_url)
SessionLocal = _database_runtime.session_factory
database_maintenance_gate = _database_runtime.maintenance_gate
engine = _database_runtime.engine


def _game_data():
    return get_game_data(settings)


def _build_planner(db):
    return RunPlanner(
        SqlitePlannerGateway(db, settings),
        LocalGameDataGateway(settings),
        LocalBuildKnowledgeGateway(settings),
        SystemClock(),
    )


def _build_today_planner(planner_factory=None):
    return TodayPlanner(
        planner_factory=planner_factory or _build_planner, game_data=_game_data(),
        configuration=settings, clock=SystemClock(), game_clock=GameClock(),
        id_generator=Uuid4IdGenerator())


def _execute_planner_for_health():
    with database_maintenance_gate.session():
        with SessionLocal() as db:
            return _build_planner(db).execute()


def _build_backup_gateway():
    return LocalBackupGateway(
        configuration=settings, clock=SystemClock(), id_generator=Uuid4IdGenerator(),
        maintenance_gate=database_maintenance_gate, database_engine=engine)


def _build_mutation_uow(*, clock=None, id_generator=None):
    return SqliteMutationUnitOfWork(
        SessionLocal,
        database_maintenance_gate,
        _build_backup_gateway(),
        clock or SystemClock(),
        id_generator or Uuid4IdGenerator(),
    )
from projectg.interface_adapters.controllers.overview_controller import OverviewController


def build_account_import_controller() -> AccountImportController:
    clock = SystemClock()
    id_generator = Uuid4IdGenerator()
    parser = GoodDocumentParser(GoodImporter(_game_data()))
    gateway = SqliteAccountImportGateway(
        SessionLocal,
        database_maintenance_gate,
        AccountImportContextReader(settings),
        AccountImportRawDocumentStorage(settings.snapshot_dir),
        _build_mutation_uow(clock=clock, id_generator=id_generator),
    )
    storage = LocalFileStorage()
    preview_import = PreviewAccountImport(gateway, parser)
    commit_import = CommitAccountImport(gateway, parser, clock, id_generator)
    return AccountImportController(
        game_data=_game_data(),
        preview_good=PreviewGoodFile(storage, preview_import),
        commit_good=CommitGoodFile(storage, commit_import),
        preview_import=preview_import,
        commit_import=commit_import,
    )


def build_settings_controller() -> SettingsController:
    gateway = SqliteSettingsGateway(
        SessionLocal, database_maintenance_gate, settings, _build_mutation_uow())
    return SettingsController(GetSettings(gateway), SaveSettings(gateway))


def build_teams_controller() -> TeamsController:
    gateway = SqliteTeamsGateway(
        SessionLocal, database_maintenance_gate, settings, _build_mutation_uow())
    return TeamsController(GetTeams(gateway), SaveTeams(gateway))


def build_character_configuration_controller() -> CharacterConfigurationController:
    gateway = SqliteCharacterConfigurationGateway(
        SessionLocal, database_maintenance_gate, settings, _build_mutation_uow())
    return CharacterConfigurationController(
        GetCharacterConfiguration(gateway), SaveCharacterConfiguration(gateway))


def build_build_intent_controller() -> BuildIntentController:
    return BuildIntentController(SqliteBuildIntentGateway(
        SessionLocal, _build_mutation_uow(), settings.account_id))


def build_game_data_controller() -> GameDataController:
    storage = LocalGameDataPackStorage(
        settings.game_data_path, SystemClock(), Uuid4IdGenerator())
    account_gateway = SqliteGameDataAccountGateway(
        SessionLocal, database_maintenance_gate, settings.account_id)
    return GameDataController(
        GetInstalledGameDataStatus(storage, account_gateway),
        PreviewGameDataPack(storage, account_gateway),
        InstallGameDataPack(storage, account_gateway),
        ExportGameDataPack(storage),
    )


def build_artifact_exchange_controller() -> ArtifactExchangeController:
    gateway = SqliteArtifactExchangeGateway(
        SessionLocal, database_maintenance_gate, settings, _build_mutation_uow(), _game_data())
    return ArtifactExchangeController(
        PreviewArtifactExchange(gateway, AefArtifactDocumentParser()),
        ConfirmArtifactExchange(gateway))


def build_planner_state_controller() -> PlannerStateController:
    gateway = SqlitePlannerStateGateway(
        SessionLocal, database_maintenance_gate, settings, _build_today_planner,
        _build_mutation_uow())
    return PlannerStateController(
        ListPlanRuns(gateway), ReplayPlanRun(gateway), PreviewPin(gateway), SetPin(gateway))


def build_target_controller() -> TargetController:
    gateway = SqliteTargetGateway(
        SessionLocal, database_maintenance_gate, settings, _game_data, _build_mutation_uow())
    document_source = JsonTargetDocumentSource()
    return TargetController(
        PreviewTargetFile(gateway, document_source),
        PreviewTargetPayload(gateway, document_source),
        CommitTargets(gateway, document_source),
        CreateTargetPreset(gateway),
        ActivateTargetPreset(gateway),
    )


def build_tier_pack_controller() -> TierPackController:
    gateway = SqliteTierPackGateway(
        SessionLocal, database_maintenance_gate, settings, _game_data(), _build_mutation_uow())
    return TierPackController(
        GetTierPack(gateway), SaveTierPack(gateway), ValidateTierPack(gateway), LocalFileStorage())


def build_support_controller() -> SupportController:
    gateway = SqliteSupportGateway(SessionLocal, database_maintenance_gate, settings)
    backup_gateway = _build_backup_gateway()
    health_gateway = SqliteDataHealthFactsGateway(
        SessionLocal, database_maintenance_gate, settings.account_id)
    return SupportController(
        GetHistory(gateway), CompareHistory(gateway),
        GetDataHealth(health_gateway, _execute_planner_for_health, LocalGameDataGateway(settings)),
        CreateBackup(backup_gateway), RestoreBackup(backup_gateway), GetLogsDirectory(gateway))


def build_overview_controller() -> OverviewController:
    return OverviewController(GetOverview(
        SqliteOverviewGateway(SessionLocal, database_maintenance_gate, settings,
                              _game_data,
                              lambda character_keys: load_build_pack(
                                  settings.build_profiles_path, character_keys=character_keys),
                              GameClock(), _build_today_planner,
                              _build_planner)))
