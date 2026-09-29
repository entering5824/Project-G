from datetime import date

import pytest

from projectg.domain.costs.models import CostStatus, ResolvedCost
from projectg.domain.game_catalog.models import DomainDefinition, GameData, Material
from projectg.domain.planning.models import GoalType, UpgradeGoal
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.domain.planning.today.compiler import TaskCompiler
from projectg.domain.planning.today.selection import TodaySelectionState, select_today_task
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.domain.planning.models import PlannerInput
from projectg.domain.planning.scorer import score_goal


def goal(key="YaeMiko", kind=GoalType.WEAPON_LEVEL, score=80):
    return UpgradeGoal(key, f"{key}:{kind.value}", key, kind, 80, 90, 1, .5, 1, 0, 0,
                       final_score=score, strategic_target=90)


@pytest.mark.parametrize("category", ["MORA", "CHARACTER_EXP", "WEAPON_EXP", "NORMAL_BOSS", "WEEKLY_BOSS", "CROWN"])
def test_resource_requirements_never_change_goal_score_or_availability(category):
    game = GameData({}, materials={"resource": Material("resource", category, category)})
    compiler = TaskCompiler(game, AvailabilityService(unavailable_sources={"resource"}, resin=0))
    compiled = []
    for quantity in (0, 1, 10000000):
        sections, _ = compiler.compile([(goal(), ResolvedCost({"resource": quantity}, CostStatus.ESTIMATED))],
                                      game_date=date(2026, 9, 28), server_region="ASIA")
        assert not sections["blocked"] and not sections["unavailable"]
        task = sections["farming"][0]
        assert task["score"] == 80
        assert task["primaryGoal"]["goalKey"] == "YaeMiko:WEAPON_LEVEL"
        assert task["title"] == "YaeMiko — Weapon 80 → 90"
        assert "sharedBonus" not in task and "missingResources" not in task
        compiled.append(task["id"])
    assert len(set(compiled)) == 1


def test_closed_talent_book_domain_defers_to_next_strategic_goal():
    game = GameData({}, materials={"book": Material("book", "Book", "TALENT_BOOK", family_key="Wisdom")},
                    domains={"domain": DomainDefinition("domain", "TALENT", ("Wisdom",), "TUE_FRI")})
    ranked = [(goal(kind=GoalType.TALENT_SKILL, score=90), ResolvedCost({"book": 1}, CostStatus.ESTIMATED)),
              (goal(key="Furina", score=30), ResolvedCost({}, CostStatus.ESTIMATED))]
    sections, _ = TaskCompiler(game).compile(ranked, game_date=date(2026, 9, 28), server_region="ASIA")
    assert len(sections["unavailable"]) == 1
    selection = select_today_task(**{key: sections[name] for key, name in
        (("quick_actions", "quickActions"), ("farming", "farming"), ("unavailable", "unavailable"), ("blocked", "blocked"))},
        state=TodaySelectionState(), strategic_order=[item.goal_key for item, _ in ranked], unresolved=[],
        config_version="1", reorder_threshold=10)
    assert selection.primary_task["primaryGoal"]["characterKey"] == "Furina"
    assert selection.no_action_reason is None
    sunday, _ = TaskCompiler(game).compile(ranked, game_date=date(2026, 9, 27), server_region="ASIA")
    assert not sunday["unavailable"]
    assert sunday["farming"][0]["score"] == sections["unavailable"][0]["score"] == 90


def test_talent_books_do_not_gate_a_weapon_goal_and_zero_books_do_not_gate_talent():
    game = GameData({}, materials={"book": Material("book", "Book", "TALENT_BOOK", family_key="Wisdom")},
                    domains={"domain": DomainDefinition("domain", "TALENT", ("Wisdom",), "TUE_FRI")})
    for kind, amount in ((GoalType.WEAPON_LEVEL, 1), (GoalType.TALENT_SKILL, 0)):
        sections, _ = TaskCompiler(game).compile([(goal(kind=kind), ResolvedCost({"book": amount}, CostStatus.ESTIMATED))],
                                                game_date=date(2026, 9, 28), server_region="ASIA")
        assert not sections["unavailable"]
        assert sections["farming"][0]["score"] == 80


def test_ten_characters_sharing_mora_still_have_ten_component_tasks():
    game = GameData({}, materials={"Mora": Material("Mora", "Mora", "MORA")})
    ranked = [(goal(key=f"Character{i}"), ResolvedCost({"Mora": 100}, CostStatus.ESTIMATED)) for i in range(10)]
    sections, _ = TaskCompiler(game).compile(ranked, game_date=date(2026, 9, 28), server_region="ASIA")
    assert len(sections["farming"]) == 10
    assert all(task["type"] == "GOAL_ACTION" and task["score"] == 80 for task in sections["farming"])


@pytest.mark.parametrize("tier_score,multiplier", [(16, .2), (17, .5), (33, .5), (34, 1), (90, 1)])
def test_low_tier_discount_belongs_to_component_score(tier_score, multiplier):
    inp = PlannerInput({}, {}, {}, {}, {}, set(), DEFAULT_PLANNER_CONFIG)
    baseline = score_goal(goal(), inp).final_score
    inp.tier_scores = {"YaeMiko": tier_score}
    discounted = score_goal(goal(), inp)
    assert discounted.final_score == pytest.approx(baseline * multiplier)
    assert discounted.score_breakdown.to_dict()["tierPriorityMultiplier"] == multiplier
