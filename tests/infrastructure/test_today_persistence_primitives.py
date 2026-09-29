from projectg.bootstrap.settings import settings
from projectg.domain.planning.today.selection import TodaySelectionState
from projectg.infrastructure.persistence.sqlite.models import Account, CharacterTargetVersion
from projectg.infrastructure.persistence.sqlite.today import (
    TodayContextReader,
    TodayPlanRunRepository,
    TodayStateRepository,
)


def test_today_context_reader_maps_only_account_facts(db_session):
    db_session.add(Account(
        id="main",
        name="Main",
        server_region="EU",
        game_language="vi",
        world_level=7,
        resin=123,
        weekly_claimed_json=["boss-a"],
        unavailable_sources_json=["domain-x"],
    ))
    db_session.flush()

    facts = TodayContextReader(settings).account(db_session)

    assert facts is not None
    assert facts.account_id == "main"
    assert facts.server_region == "EU"
    assert facts.game_language == "vi"
    assert facts.world_level == 7
    assert facts.resin == 123
    assert facts.weekly_claimed == ("boss-a",)
    assert facts.unavailable_sources == ("domain-x",)


def test_today_state_repository_round_trips_domain_selection_state(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.flush()
    repository = TodayStateRepository()
    expected = TodaySelectionState(
        pursued_task_id="farm:raiden",
        pursued_character_key="RaidenShogun",
        pursued_score=91.5,
        ordering_group="character:RaidenShogun",
        pursued_config_version="planner-v2",
        pinned_character_key="RaidenShogun",
    )

    repository.save(db_session, "main", expected)

    assert repository.load(db_session, "main") == expected


def test_today_plan_run_repository_reads_latest_target_version(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.add_all([
        CharacterTargetVersion(
            account_id="main", character_key="RaidenShogun", preset_key="default",
            version=1, target_json={},
        ),
        CharacterTargetVersion(
            account_id="main", character_key="RaidenShogun", preset_key="default",
            version=3, target_json={},
        ),
        CharacterTargetVersion(
            account_id="main", character_key="Fischl", preset_key="default",
            version=2, target_json={},
        ),
    ])
    db_session.flush()

    assert TodayPlanRunRepository._target_versions(db_session, "main") == {
        "Fischl": 2,
        "RaidenShogun": 3,
    }
