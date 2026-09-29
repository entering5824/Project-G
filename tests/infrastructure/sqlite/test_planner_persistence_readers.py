from dataclasses import fields, is_dataclass
from collections.abc import Mapping

from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.base import Base
from projectg.infrastructure.persistence.sqlite.models import (
    CharacterPriority, Account, Snapshot, SnapshotCharacter, SnapshotTeam, PlannerTeam, SnapshotArtifact,
)
from projectg.infrastructure.persistence.sqlite.planner_gateway import SqlitePlannerGateway
from projectg.application.planning.input import prepare_planner_input
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG


def _assert_detached(value):
    assert not isinstance(value, Base)
    if is_dataclass(value):
        for field in fields(value):
            _assert_detached(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for item in value.values():
            _assert_detached(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _assert_detached(item)


def test_missing_snapshot_keeps_default_fact_behavior(db_session):
    gateway = SqlitePlannerGateway(db_session, Settings(account_id="missing"))
    facts = gateway.load_facts()
    assert not facts.has_snapshot
    assert facts.characters == facts.teams == facts.artifact_evaluations == ()
    assert gateway.load_config() == DEFAULT_PLANNER_CONFIG
    _assert_detached(facts)


def test_snapshot_facts_are_detached_and_application_owns_team_projection(db_session):
    db_session.add(Account(id="a", name="A", server_region="ASIA"))
    db_session.flush()
    db_session.add(Snapshot(id="s", account_id="a", good_format="GOOD", raw_file_hash="hash", canonical_state_hash="state", importer_version="test", raw_path="snapshot.json"))
    db_session.flush()
    db_session.get(Account, "a").current_snapshot_id = "s"
    db_session.add(SnapshotCharacter(snapshot_id="s", character_key="Amber", level=80,
        ascension=5, constellation=1, talent_auto=8, talent_skill=8, talent_burst=8))
    db_session.add(CharacterPriority(account_id="a", character_key="Amber", override="PRIORITIZED"))
    db_session.add(SnapshotTeam(snapshot_id="s", team_id="t", members_json=["Amber", "Amber"]))
    db_session.add(PlannerTeam(account_id="a", team_id="p", name="Primary",
        members_json=["Fischl"], is_primary=True))
    db_session.add(SnapshotArtifact(snapshot_id="s", artifact_instance_id="art",
        character_key="Amber", set_key="SetA", slot_key="flower", rarity=5, level=20,
        main_stat_key="hp", substats_json=[], rv=100, rv_status="KNOWN"))
    db_session.flush()
    facts = SqlitePlannerGateway(db_session, Settings(account_id="a")).load_facts()
    _assert_detached(facts)
    db_session.expunge_all()
    assert facts.teams[0].members == ("Amber", "Amber")
    assert facts.characters[0].artifacts["flower"].set_key == "SetA"
    assert facts.characters[0].artifact_fingerprint
    prepared = prepare_planner_input(facts, GameData(metadata={}), None, DEFAULT_PLANNER_CONFIG).value
    assert prepared.priority_overrides == {"Amber": "PRIORITIZED"}
    assert prepared.saved_team_members == {"Amber", "Fischl"}
    assert prepared.primary_team_members == {"Fischl"}
    assert prepared.characters["Amber"].artifacts["flower"] == {
        "setKey": "SetA", "rv": 100, "rvStatus": "KNOWN", "level": 20, "mainStat": "hp"}


