from types import SimpleNamespace

from sqlalchemy import func, select

from projectg.infrastructure.persistence.sqlite.planner_state_gateway import SqlitePlannerStateGateway
from projectg.application.use_cases.planner_state.replay_plan_run import ReplayPlanRun, ReplayPlanRunRequest
from projectg.application.use_cases.planner_state.preview_pin import PreviewPin, PreviewPinRequest
from projectg.infrastructure.clock.system_clock import SystemClock
from projectg.infrastructure.ids.uuid_generator import Uuid4IdGenerator
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork
from projectg.bootstrap.settings import settings
from projectg.infrastructure.persistence.sqlite.models import Account, CharacterTargetVersion, PlanRun, TodayState, SnapshotCharacter
from projectg.bootstrap.dependencies import _build_today_planner



def _mutation_uow(factory, gate):
    return SqliteMutationUnitOfWork(
        factory, gate, SimpleNamespace(before_mutation=lambda db, reason: None),
        SystemClock(), Uuid4IdGenerator())

def task(task_id: str, character: str, score: float) -> dict:
    return {"id": task_id, "title": task_id, "score": score,
            "primaryGoal": {"goalKey": f"{character}:LEVEL", "characterKey": character},
            "characterKeys": [character], "requiredResources": {}, "resourceInfo": {}}


def output(*tasks: dict) -> dict:
    return {"generatedAt": "2026-09-24T00:00:00Z", "gameDate": "2026-09-24",
            "weekday": "THURSDAY", "serverRegion": "ASIA", "inventoryVersion": 0,
            "globalGoals": [], "quickActions": list(tasks), "farming": [],
            "unavailable": [], "blocked": [], "unresolved": []}


def test_today_hysteresis_persists_and_planrun_replay_is_immutable(db_session, monkeypatch):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.add(TodayState(account_id="main", pursued_task_id="old",
                              pursued_character_key="A", pursued_score=80,
                              ordering_group="character:A", pursued_config_version="1"))
    db_session.commit()
    planner = _build_today_planner()
    result = SimpleNamespace(planner_version="1.0.0")

    first = output(task("new", "A", 82), task("old", "A", 80))
    planner._select_and_persist(db_session, db_session.get(Account, "main"), first, {}, result, config="1")
    assert first["primaryTask"]["id"] == "old"
    assert first["todayState"]["switchThreshold"] == 3.0

    second = output(task("new", "A", 84), task("old", "A", 80))
    planner._select_and_persist(db_session, db_session.get(Account, "main"), second, {}, result, config="1")
    assert second["primaryTask"]["id"] == "new"
    assert db_session.scalar(select(func.count()).select_from(PlanRun)) == 2

    run = db_session.scalars(select(PlanRun).order_by(PlanRun.created_at.desc(), PlanRun.id.desc())).first()
    recorded = dict(run.result_json)
    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqlitePlannerStateGateway(
        factory, gate, settings, _build_today_planner, _mutation_uow(factory, gate),
    )
    replay = ReplayPlanRun(gateway).execute(ReplayPlanRunRequest(run.id))
    assert replay.result == recorded
    assert replay.context["gameDate"] == "2026-09-24"
    assert replay.switch_threshold == 3.0


def test_pin_wins_today_only_and_config_change_bypasses_hysteresis(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.add(TodayState(account_id="main", pursued_task_id="old",
                              pursued_character_key="A", pursued_score=100,
                              ordering_group="character:A", pursued_config_version="1",
                              pinned_character_key="B"))
    db_session.commit()
    planner = _build_today_planner(); result = SimpleNamespace(planner_version="1.0.0")
    pinned = output(task("a", "A", 100), task("b", "B", 10))
    planner._select_and_persist(db_session, db_session.get(Account, "main"), pinned, {}, result, config="1")
    assert pinned["primaryTask"]["id"] == "b"
    assert pinned["todayState"]["pinStatus"] == "ACTIVE"

    state = db_session.get(TodayState, "main")
    state.pinned_character_key = None
    state.pursued_task_id = "old"
    state.pursued_character_key = "A"
    state.ordering_group = "character:A"
    state.pursued_config_version = "1"
    db_session.commit()
    changed = output(task("new", "A", 81), task("old", "A", 80))
    planner._select_and_persist(db_session, db_session.get(Account, "main"), changed, {}, result, config="2")
    assert changed["primaryTask"]["id"] == "new"


def test_completed_pin_remains_persisted_with_completed_status(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.add(CharacterTargetVersion(account_id="main", character_key="A",
        preset_key="default", version=1, target_json={}))
    db_session.add(TodayState(account_id="main", pinned_character_key="A"))
    db_session.commit()
    plan = output()
    _build_today_planner()._select_and_persist(db_session, db_session.get(Account, "main"), plan, {},
        SimpleNamespace(planner_version="1.0.0"), config="1")
    assert plan["todayState"]["pinnedCharacterKey"] == "A"
    assert plan["todayState"]["pinStatus"] == "COMPLETED"


def test_today_follows_global_character_order_before_task_score(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.commit()
    planner = _build_today_planner()
    result = SimpleNamespace(planner_version="1.0.0", global_plan=[
        SimpleNamespace(character_key="HighTier", goal_key="HighTier:LEVEL"),
        SimpleNamespace(character_key="LowTier", goal_key="LowTier:LEVEL"),
    ])
    plan = output(task("high", "HighTier", 30), task("low", "LowTier", 99))

    planner._select_and_persist(db_session, db_session.get(Account, "main"), plan, {}, result, config="1")

    assert plan["primaryTask"]["id"] == "high"
    assert plan["decisionMode"] == "STRATEGIC"
    assert plan["noActionReason"] is None
    assert [item["id"] for item in plan["alternativeTasks"]] == ["low"]


def test_today_defers_unavailable_goal_to_next_strategic_goal(db_session):
    db_session.add(Account(id="main", name="Main", server_region="ASIA"))
    db_session.commit()
    planner = _build_today_planner()
    result = SimpleNamespace(planner_version="1.0.0", global_plan=[
        SimpleNamespace(character_key="HighTier", goal_key="HighTier:LEVEL"),
        SimpleNamespace(character_key="LowTier", goal_key="LowTier:LEVEL"),
    ])
    closed = task("closed", "HighTier", 25)
    low = task("low", "LowTier", 99)
    plan = output(low)
    plan["unavailable"] = [closed]

    planner._select_and_persist(db_session, db_session.get(Account, "main"), plan, {}, result, config="1")

    assert plan["primaryTask"]["id"] == "low"
    assert plan["noActionReason"] is None
    assert [item["id"] for item in plan["alternativeTasks"]] == ["closed"]


def test_pin_preview_compares_against_real_today_primary_not_highest_task_score(db_session, monkeypatch):
    db_session.add(Account(id="main", name="Main", server_region="ASIA",
                           current_snapshot_id="snapshot"))
    db_session.add(SnapshotCharacter(snapshot_id="snapshot", character_key="Pinned", level=80,
        ascension=5, constellation=0, talent_auto=1, talent_skill=1, talent_burst=1))
    db_session.commit()
    primary = task("strategic", "CurrentPriority", 10)
    higher_raw_score = task("high-score", "Other", 99)
    proposed = task("pinned-task", "Pinned", 20)

    class FakeToday:
        def generate(self, db):
            return output(primary, higher_raw_score, proposed) | {"primaryTask": primary}

    factory = lambda: db_session
    gate = DatabaseMaintenanceGate()
    gateway = SqlitePlannerStateGateway(
        factory, gate, settings, FakeToday, _mutation_uow(factory, gate),
    )
    preview = PreviewPin(gateway).execute(PreviewPinRequest("Pinned"))

    assert preview.strategic_task["id"] == "strategic"
    assert preview.candidate["id"] == "pinned-task"
