from types import SimpleNamespace
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.domain.planning.tiers import label_for
from projectg.domain.planning.tier_pack import validate_tier_pack
from projectg.infrastructure.persistence.sqlite.repositories.tier_pack import current_tier_pack
from projectg.infrastructure.persistence.sqlite.tier_pack_gateway import SqliteTierPackGateway
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.application.use_cases.tier_packs.save_tier_pack import SaveTierPack
from projectg.application.use_cases.tier_packs.requests import SaveTierPackRequest
from projectg.bootstrap.settings import settings
from projectg.infrastructure.persistence.sqlite.repositories.account import AccountRepository


def test_tier_pack_requires_manual_score_and_canonical_character_key():
    assert [label_for(value) for value in (100, 84, 83, 67, 66, 50, 49, 34, 33, 17, 16, 0, None)] == [
        "S+", "S+", "S", "S", "A", "A", "B", "B", "C", "C", "D", "D", "Unranked"]
    pack = validate_tier_pack({"version": 1, "ratings": {"Furina": {"score": 90, "notes": ""}},
        "minimumTierForRoadmap": "B", "controls": {}, "selectedSets": {}},
        known_keys={"Furina"}, known_sets={"GladiatorsFinale"})
    assert pack["ratings"]["Furina"]["score"] == 90


def test_tier_pack_persists_versions_and_unchanged_save_is_idempotent(db_session):
    account = AccountRepository().get_or_create(db_session, settings.account_id,
                                                settings.account_name, settings.server_region)
    payload = {"version": 1, "ratings": {"Furina": {"score": 90, "notes": "Top"}},
               "minimumTierForRoadmap": "B", "controls": {}, "selectedSets": {}}
    catalog = get_game_data(settings)
    backup_service = SimpleNamespace(before_mutation=lambda db, reason: None)
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqliteTierPackGateway(
        factory, gate, settings, catalog,
        SqliteMutationUnitOfWork(factory, gate, backup_service))
    save = SaveTierPack(gateway)
    first = save.execute(SaveTierPackRequest(payload)).values
    assert first["packVersion"] == 1
    assert save.execute(SaveTierPackRequest(payload)).values["packVersion"] == 1
    payload["ratings"]["Furina"]["score"] = 80
    assert save.execute(SaveTierPackRequest(payload)).values["packVersion"] == 2
    assert current_tier_pack(db_session, account.id)["ratings"]["Furina"]["score"] == 80


