from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
import json
import sqlite3
from types import SimpleNamespace
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import func, select

from projectg.infrastructure.persistence.sqlite.overview_gateway import SqliteOverviewGateway
from projectg.application.use_cases.overview.get_overview import GetOverview
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.clock.game_clock import GameClock
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.persistence.sqlite.today_planner import TodayPlanner
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.infrastructure.game_data.json.build_profiles import load_build_pack
from projectg.infrastructure.serialization.good_importer import GoodImporter
from projectg.infrastructure.serialization.good_document import GoodDocumentParser
from projectg.bootstrap.settings import settings
from projectg.infrastructure.persistence.sqlite.models import Account, Snapshot, CharacterTargetVersion, ArtifactEvaluation, TierPackVersion
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository
from projectg.application.imports.errors import AbnormalAccountChangeError
from projectg.application.use_cases.imports.preview_account_import import PreviewAccountImport, PreviewAccountImportRequest
from projectg.application.use_cases.imports.commit_account_import import CommitAccountImport, CommitAccountImportRequest
from projectg.infrastructure.filesystem.account_import_raw_storage import AccountImportRawDocumentStorage
from projectg.infrastructure.persistence.sqlite.account_import import AccountImportContextReader
from projectg.infrastructure.persistence.sqlite.account_import_gateway import SqliteAccountImportGateway
from projectg.bootstrap.desktop_environment import prepare_desktop_environment, migrate_desktop_database, SCHEMA_HEAD
from projectg.domain.targets.validation import validate_target
from projectg.application.use_cases.targets.preview_target_payload import PreviewTargetPayload, PreviewTargetPayloadRequest
from projectg.application.use_cases.targets.commit_targets import CommitTargets, CommitTargetRequest
from projectg.application.use_cases.targets.create_target_preset import CreateTargetPreset, CreateTargetPresetRequest
from projectg.application.use_cases.targets.activate_target_preset import ActivateTargetPreset, ActivateTargetPresetRequest
from projectg.infrastructure.persistence.sqlite.target_gateway import SqliteTargetGateway
from projectg.infrastructure.serialization.target_document_source import JsonTargetDocumentSource
from projectg.infrastructure.persistence.sqlite.artifact_exchange_gateway import SqliteArtifactExchangeGateway
from projectg.infrastructure.persistence.sqlite.settings_gateway import SqliteSettingsGateway
from projectg.infrastructure.persistence.sqlite.teams_gateway import SqliteTeamsGateway
from projectg.infrastructure.persistence.sqlite.character_configuration_gateway import SqliteCharacterConfigurationGateway
from projectg.application.use_cases.settings.get_settings import GetSettings
from projectg.application.use_cases.settings.save_settings import SaveSettings, SaveSettingsRequest
from projectg.application.use_cases.teams.get_teams import GetTeams
from projectg.application.use_cases.teams.save_teams import SaveTeams, SaveTeamsRequest
from projectg.application.use_cases.characters.get_configuration import GetCharacterConfiguration
from projectg.application.use_cases.characters.save_configuration import SaveCharacterConfiguration, SaveCharacterConfigurationRequest
from projectg.infrastructure.serialization.aef_exchange import AefArtifactDocumentParser
from projectg.application.use_cases.artifacts.preview_exchange import PreviewArtifactExchange, PreviewArtifactExchangeRequest
from projectg.application.use_cases.artifacts.confirm_exchange import ConfirmArtifactExchange, ConfirmArtifactExchangeRequest
from projectg.infrastructure.persistence.sqlite.planner_state_gateway import SqlitePlannerStateGateway
from projectg.application.use_cases.planner_state.preview_pin import PreviewPin, PreviewPinRequest
from projectg.application.use_cases.planner_state.set_pin import SetPin, SetPinRequest
from projectg.infrastructure.game_data.json.pack_storage import LocalGameDataPackStorage
from projectg.infrastructure.persistence.sqlite.game_data_account_gateway import SqliteGameDataAccountGateway
from projectg.application.use_cases.game_data.preview_pack import PreviewGameDataPack
from projectg.application.use_cases.game_data.install_pack import InstallGameDataPack
from projectg.application.use_cases.game_data.requests import GameDataPathRequest
from projectg.interface_adapters.mappers.target_contract import target_contract_bundle
from projectg.infrastructure.persistence.sqlite.models import PlanRun, PlannerTeam, TodayState
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.infrastructure.persistence.sqlite.today_planner import TodayPlanner
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


def _game_data():
    return get_game_data(settings)


def _account_imports(db_session, snapshot_dir):
    configuration = settings.model_copy(update={"snapshot_dir": Path(snapshot_dir)})
    clock = SystemClock()
    ids = Uuid4IdGenerator()
    factory = lambda: nullcontext(db_session)
    gate = DatabaseMaintenanceGate()
    gateway = SqliteAccountImportGateway(
        factory, gate, AccountImportContextReader(configuration),
        AccountImportRawDocumentStorage(configuration.snapshot_dir),
        _mutation_uow(factory, gate, clock=clock, ids=ids))
    parser = GoodDocumentParser(GoodImporter(_game_data()))
    return (PreviewAccountImport(gateway, parser),
            CommitAccountImport(gateway, parser, clock, ids))


def _commit_good(db_session, snapshot_dir, value, *, allow_regression=False):
    _, commit = _account_imports(db_session, snapshot_dir)
    result = commit.execute(CommitAccountImportRequest(
        json.dumps(value).encode(), allow_regression=allow_regression))
    return db_session.get(Snapshot, result.snapshot_id), (
        db_session.get(Snapshot, result.previous_snapshot_id) if result.previous_snapshot_id else None)


def _no_backup():
    return SimpleNamespace(before_mutation=lambda db, reason: None)


def _mutation_uow(session_factory, gate=None, *, clock=None, ids=None):
    return SqliteMutationUnitOfWork(
        session_factory,
        gate or DatabaseMaintenanceGate(),
        _no_backup(),
        clock or SystemClock(),
        ids or Uuid4IdGenerator(),
    )


def _history_dependencies():
    return {"clock": SystemClock(), "id_generator": Uuid4IdGenerator()}


def _settings_actions(db_session):
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqliteSettingsGateway(
        factory, gate, settings, _mutation_uow(factory, gate))
    return GetSettings(gateway), SaveSettings(gateway)


def _team_actions(db_session):
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqliteTeamsGateway(
        factory, gate, settings, _mutation_uow(factory, gate))
    return GetTeams(gateway), SaveTeams(gateway)


def _character_actions(db_session):
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqliteCharacterConfigurationGateway(
        factory, gate, settings, _mutation_uow(factory, gate))
    return GetCharacterConfiguration(gateway), SaveCharacterConfiguration(gateway)


def _target_gateway(db_session):
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    return SqliteTargetGateway(
        factory, gate, settings, _game_data, _mutation_uow(factory, gate),
    )


def _target_document_source():
    return JsonTargetDocumentSource()


def _today_planner(planner_factory=None):
    from projectg.bootstrap.dependencies import _build_today_planner
    return _build_today_planner(planner_factory)


def _planner(db_session):
    from projectg.bootstrap.dependencies import _build_planner
    return _build_planner(db_session)


def test_desktop_overview_empty_account_does_not_mutate_database(db_session):
    gateway = SqliteOverviewGateway(
        lambda: db_session, DatabaseMaintenanceGate(), settings, _game_data,
        lambda character_keys: load_build_pack(
            settings.build_profiles_path, character_keys=character_keys),
        GameClock(), _today_planner, _planner,
    )
    result = GetOverview(gateway).execute().values
    assert result == {"snapshotId": None, "today": None, "roadmap": None, "characters": []}
    assert db_session.get(Account, settings.account_id) is None


def test_good_decrease_requires_explicit_override(db_session, good_json, tmp_path):
    preview, commit = _account_imports(db_session, tmp_path / "snapshots")
    original = json.dumps(good_json).encode()
    first_result = commit.execute(CommitAccountImportRequest(original))
    first = db_session.get(Snapshot, first_result.snapshot_id)
    lowered = deepcopy(good_json)
    lowered["characters"][0]["level"] -= 1
    raw = json.dumps(lowered).encode()
    preview_result = preview.execute(PreviewAccountImportRequest(raw))
    assert list(preview_result.abnormal_changes) == [
        {"characterKey": "RaidenShogun", "field": "level", "before": 80, "after": 79}]
    with pytest.raises(AbnormalAccountChangeError):
        commit.execute(CommitAccountImportRequest(raw))
    assert db_session.get(Account, settings.account_id).current_snapshot_id == first.id
    assert len(db_session.scalars(select(Snapshot)).all()) == 1
    second_result = commit.execute(CommitAccountImportRequest(raw, allow_regression=True))
    assert second_result.snapshot_id != first.id
    assert db_session.get(Account, settings.account_id).current_snapshot_id == second_result.snapshot_id

def test_desktop_bootstrap_copies_legacy_database_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.delenv("GENSHIN_DATABASE_URL", raising=False)
    source = tmp_path / "legacy"
    destination = tmp_path / "user-data"
    snapshot = source / "snapshots" / "old.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("{}", encoding="utf-8")
    original = source / "app.db"
    connection = sqlite3.connect(original)
    connection.execute("CREATE TABLE snapshots (id TEXT PRIMARY KEY, raw_path TEXT)")
    connection.execute("INSERT INTO snapshots VALUES (?, ?)", ("s1", str(snapshot)))
    connection.commit()
    connection.close()
    new_database = prepare_desktop_environment(destination=destination, legacy_data=source)
    assert new_database == destination / "app.db"
    assert original.is_file() and snapshot.is_file()
    with sqlite3.connect(new_database) as copied:
        path = copied.execute("SELECT raw_path FROM snapshots WHERE id='s1'").fetchone()[0]
    assert path == str(destination / "snapshots" / "old.json")
    assert (destination / "snapshots" / "old.json").read_text(encoding="utf-8") == "{}"


def test_desktop_migration_can_create_fresh_schema_without_http(tmp_path, monkeypatch):
    database = tmp_path / "fresh-desktop.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database.as_posix()}")

    migrate_desktop_database()

    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        planner_team_columns = {row[1] for row in connection.execute("PRAGMA table_info(planner_teams)")}
    assert revision == SCHEMA_HEAD
    assert "is_primary" in planner_team_columns


def test_target_import_selects_valid_rows_and_retries_once(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    target = {
        "level": 80, "ascension": 5, "importance": {"level": 0.8, "ascension": 0.8},
        "talents": {name: {"enabled": False, "target": 1, "importance": 0.0}
                    for name in ("normal", "skill", "burst")},
        "weapon": {"targetLevel": 1, "importance": 0.0},
        "artifact": {"enabled": False, "targetQuality": "GOOD", "importance": 0.0,
                     "primarySets": [], "alternativeSets": [], "gate": {}},
        "notes": "selected desktop target",
    }
    payload = {"version": 1, "targets": {"Fischl": target, "RaidenShogun": [],
                                         "UnknownCharacter": target}}
    gateway = _target_gateway(db_session)
    source = _target_document_source()
    preview = PreviewTargetPayload(gateway, source).execute(
        PreviewTargetPayloadRequest(payload)).preview
    assert preview["validTargets"] == ["Fischl"]
    assert preview["invalidTargets"][0]["characterKey"] == "RaidenShogun"
    assert preview["unknownCharacters"] == ["UnknownCharacter"]
    detail = preview["validTargetDetails"][0]
    assert detail["characterKey"] == "Fischl"
    assert detail["currentVersion"] is None
    assert detail["target"]["level"] == 80
    assert preview["overwrites"] == []

    commit = CommitTargets(gateway, source)
    request = CommitTargetRequest(payload, frozenset({"Fischl"}), "desktop-target-operation-1")
    first = commit.execute(request).values
    replay = commit.execute(request).values
    assert replay == first
    assert [row.character_key for row in db_session.scalars(select(CharacterTargetVersion)).all()] == ["Fischl"]
    refreshed_preview = PreviewTargetPayload(gateway, source).execute(
        PreviewTargetPayloadRequest(payload)).preview
    assert refreshed_preview["overwrites"] == [{"characterKey": "Fischl", "currentVersion": 1,
                                                 "newVersion": 2}]

def test_desktop_artifact_preview_then_confirm_is_direct_and_versioned(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqliteArtifactExchangeGateway(
        factory, gate, settings, _mutation_uow(factory, gate), _game_data())
    payload = {"format": "AEF", "version": 1, "characterKey": "RaidenShogun",
               "metrics": {"rv": 250}}
    preview_result = PreviewArtifactExchange(gateway, AefArtifactDocumentParser()).execute(
        PreviewArtifactExchangeRequest(payload))
    preview = {"snapshotId": preview_result.snapshot_id,
               "evaluations": list(preview_result.evaluations),
               "validCount": preview_result.valid_count}
    assert preview["validCount"] == 1
    assert preview["evaluations"][0]["quality"]["qualityStatus"] == "NEEDS_QUALITY_CONFIG"
    saved_result = ConfirmArtifactExchange(gateway).execute(
        ConfirmArtifactExchangeRequest((preview["evaluations"][0],), preview["snapshotId"]))
    saved = {"evaluations": list(saved_result.evaluations)}
    assert saved["evaluations"][0]["evaluation"]["status"] == "CONFIRMED"
    assert db_session.scalar(select(func.count()).select_from(ArtifactEvaluation)) == 1


def test_desktop_settings_save_versioned_planner_and_artifact_config(db_session):
    AccountRepository().get_or_create(db_session, settings.account_id,
                                      settings.account_name, settings.server_region)
    get_settings, save_settings = _settings_actions(db_session)
    current = get_settings.execute()
    planner = deepcopy(current.planner); planner["reorderThreshold"] = 4.0
    planner["manualOrderEnabled"] = True
    planner["manualOrder"] = ["RaidenShogun", "Fischl"]
    artifact = {"adapterType": "rv", "thresholds": {
        "POOR": 100.0, "ACCEPTABLE": 200.0, "GOOD": 300.0, "EXCELLENT": 400.0}}
    saved = save_settings.execute(SaveSettingsRequest(planner, artifact, {
        "serverRegion": "EUROPE", "gameLanguage": "vi", "worldLevel": 7,
        "resin": 0, "weeklyClaimed": ["Stormterror"],
        "unavailableSources": ["FreedomDomain"]}))
    assert saved.planner["reorderThreshold"] == 4.0
    assert saved.planner["manualOrderEnabled"] is True
    assert saved.planner["manualOrder"] == ["RaidenShogun", "Fischl"]
    assert saved.artifact_configured is True
    assert saved.artifact["thresholds"]["GOOD"] == 300.0
    assert saved.account == {"serverRegion": "EUROPE", "gameLanguage": "vi",
        "worldLevel": 7, "resin": 0, "weeklyClaimed": ["Stormterror"],
        "unavailableSources": ["FreedomDomain"]}


def test_desktop_pin_can_use_snapshot_inferred_build_target(db_session, good_json, tmp_path, monkeypatch):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    db_session.add(TierPackVersion(account_id=account.id, version=1, pack_json={
        "version": 1, "ratings": {"RaidenShogun": {"score": 90, "notes": ""}},
        "minimumTierForRoadmap": "B", "controls": {}, "selectedSets": {}}))
    db_session.commit()
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqlitePlannerStateGateway(
        factory, gate, settings, _today_planner, _mutation_uow(factory, gate),
    )
    preview = PreviewPin(gateway).execute(PreviewPinRequest("RaidenShogun"))
    assert preview.status == "READY"
    SetPin(gateway).execute(SetPinRequest("RaidenShogun"))
    state = db_session.get(TodayState, settings.account_id)
    assert state.pinned_character_key == "RaidenShogun"
    PreviewPin(gateway).execute(PreviewPinRequest("RaidenShogun"))
    run = db_session.scalars(select(PlanRun).order_by(PlanRun.created_at.desc(), PlanRun.id.desc())).first()
    assert run.result_json["todayState"]["pinStatus"] == "ACTIVE"


def test_desktop_team_configuration_is_separate_from_good_and_feeds_planner(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    get_teams, save_teams = _team_actions(db_session)
    loaded = get_teams.execute()
    assert loaded.imported_teams[0]["name"] == "Overload"
    saved = save_teams.execute(SaveTeamsRequest(({
        "teamId": "abyss-a", "name": "Abyss A",
        "members": ["RaidenShogun"], "isPrimary": True},)))
    assert saved.configured_teams[0]["teamId"] == "abyss-a"
    assert saved.configured_teams[0]["isPrimary"] is True
    assert db_session.scalar(select(func.count()).select_from(PlannerTeam)) == 1
    planner_input = _planner(db_session).execute(
        candidate_config=DEFAULT_PLANNER_CONFIG).planner_input
    assert "RaidenShogun" in planner_input.saved_team_members
    assert "RaidenShogun" in planner_input.primary_team_members
    with pytest.raises(ValueError, match="unowned"):
        save_teams.execute(SaveTeamsRequest(({
            "name": "Bad", "members": ["UnknownCharacter"]},)))
    with pytest.raises(ValueError, match="Only one"):
        save_teams.execute(SaveTeamsRequest((
            {"name":"A","members":["RaidenShogun"],"isPrimary":True},
            {"name":"B","members":["Fischl"],"isPrimary":True},
        )))


def test_target_contract_bundle_is_versioned_and_uses_real_import_shape():
    bundle = target_contract_bundle()
    assert bundle["version"] == 1
    assert bundle["schema"]["properties"]["version"]["const"] == 1
    assert bundle["example"]["version"] == 1
    assert set(bundle["example"]["targets"]["Nahida"]["talents"]) == {"normal", "skill", "burst"}
    assert "Không tính Mora/material/cost" in bundle["prompt"]


def test_target_weapon_intent_is_not_rejected_by_outdated_local_gamedata():
    target = target_contract_bundle()["example"]["targets"]["Nahida"]
    target = deepcopy(target)
    target["weapon"]["weaponKey"] = "FutureWeaponNotInInstalledPack"
    validated = validate_target(target)
    assert validated["weapon"]["weaponKey"] == "FutureWeaponNotInInstalledPack"


def test_game_data_pack_preview_and_atomic_install(db_session, tmp_path, monkeypatch):
    from projectg.infrastructure.game_data.json.loader import DATASET
    installed = tmp_path / "game_data" / "game_data.json"
    installed.parent.mkdir(parents=True)
    installed.write_bytes(DATASET.read_bytes())
    monkeypatch.setattr(settings, "game_data_path", installed)

    candidate = tmp_path / "candidate.json"
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    raw["metadata"]["data_version"] = "desktop-pack-test-2"
    candidate.write_text(json.dumps(raw), encoding="utf-8")

    storage = LocalGameDataPackStorage(installed, SystemClock(), Uuid4IdGenerator())
    account_gateway = SqliteGameDataAccountGateway(
        lambda: nullcontext(db_session), DatabaseMaintenanceGate(), settings.account_id)

    preview = PreviewGameDataPack(storage, account_gateway).execute(
        GameDataPathRequest(str(candidate)))
    assert preview.metadata["dataVersion"] == "desktop-pack-test-2"

    result = InstallGameDataPack(storage, account_gateway).execute(
        GameDataPathRequest(str(candidate)))
    assert result.metadata["dataVersion"] == "desktop-pack-test-2"
    assert result.backup_path and Path(result.backup_path).is_file()


def test_persistent_planner_infers_targets_from_verified_basic_profiles(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)

    planner_input = _planner(db_session).execute(
        candidate_config=DEFAULT_PLANNER_CONFIG).planner_input

    assert planner_input.include_unranked_in_plan is False
    assert planner_input.tier_scores == {}
    assert "RaidenShogun" in planner_input.character_targets
    assert "Fischl" in planner_input.character_targets


def test_tiered_snapshot_generates_source_roadmap_with_dataset_hashes(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    db_session.add(TierPackVersion(account_id=account.id, version=1, pack_json={
        "version": 1, "ratings": {"RaidenShogun": {"score": 90, "notes": ""},
                                  "Fischl": {"score": 20, "notes": ""}},
        "minimumTierForRoadmap": "B", "controls": {}, "selectedSets": {}}))
    db_session.commit()
    today = _today_planner().generate(db_session)
    assert 'sourceRoadmapEnabled' not in today
    assert today['globalGoals']
    assert all(task['type']=='GOAL_ACTION' for task in today['farming'])
    assert all(task['primaryGoal']['characterKey'] != 'Fischl' for task in today['farming'])
    assert today["datasetHashes"]["tierPackVersion"] == 1
    assert today["datasetHashes"]["snapshotHash"]
    assert today["datasetHashes"]["buildKnowledgeHash"]
    assert today["datasetHashes"]["gameDataHash"]
    assert all("missingResources" not in task for task in today["farming"])


def test_desktop_character_configuration_sets_tier_and_override_without_snapshot(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    snapshot_id = account.current_snapshot_id
    get_configuration, save_configuration = _character_actions(db_session)

    initial = get_configuration.execute("Fischl")
    assert initial.tier_key is None and initial.priority_override == "NORMAL"
    saved = save_configuration.execute(SaveCharacterConfigurationRequest(
        "Fischl", "T1", "PRIORITIZED"))

    assert saved.tier_key == "T1"
    assert saved.priority_override == "PRIORITIZED"
    assert db_session.get(Account, settings.account_id).current_snapshot_id == snapshot_id


def test_target_preset_application_can_create_and_activate_without_http(db_session, good_json, tmp_path):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    _commit_good(db_session, tmp_path / "snapshots", good_json)
    target = {
        "level": 80, "ascension": 5, "importance": {"level": 0.8, "ascension": 0.8},
        "talents": {name: {"enabled": False, "target": 1, "importance": 0.0}
                    for name in ("normal", "skill", "burst")},
        "weapon": {"targetLevel": 1, "importance": 0.0},
        "artifact": {"enabled": False, "targetQuality": "GOOD", "importance": 0.0,
                     "primarySets": [], "alternativeSets": [], "gate": {}},
        "notes": "preset test",
    }
    gateway = _target_gateway(db_session)
    source = _target_document_source()
    CommitTargets(gateway, source).execute(CommitTargetRequest(
        {"version": 1, "targets": {"Fischl": target}},
        frozenset({"Fischl"}),
        "desktop-preset-target-1",
    ))
    created = CreateTargetPreset(gateway).execute(
        CreateTargetPresetRequest("Fischl", "On-field")).values
    assert created["presetKey"] == "on-field" and created["active"] is False

    activated = ActivateTargetPreset(gateway).execute(
        ActivateTargetPresetRequest("Fischl", created["presetKey"])).values
    assert activated["presetKey"] == "on-field"
    assert sum(1 for row in activated["presets"] if row["active"]) == 1
