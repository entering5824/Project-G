from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from projectg.application.planning.today import GenerateTodayPlan, TodayAccountContext
from projectg.bootstrap.settings import settings
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.domain.planning.engine import PlannerEngine
from projectg.domain.planning.models import CharacterState, PlannerInput, TierValue, WeaponState
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.domain.planning.today.selection import TodaySelectionState, select_today_task, strategic_goal_order
from projectg.infrastructure.game_data.json.repository import get_game_data


@pytest.mark.parametrize("category", ["MORA", "WEAPON_EXP", "NORMAL_BOSS"])
def test_global_and_today_priorities_ignore_zero_or_large_resource_costs(category):
    game = get_game_data(settings)
    weapon = next(item for item in game.weapons.values() if item.max_level == 90)
    characters = {key: CharacterState(key, 40, 2, {"auto": 1, "skill": 1, "burst": 1},
                                    WeaponState(key, weapon.key, 80, 6)) for key in ("YaeMiko", "Furina")}
    targets = {key: {"level": 90, "ascension": 6, "importance": {"level": .8, "ascension": .8},
                    "talents": {name: {"enabled": False, "target": 1, "importance": 0}
                                for name in ("normal", "skill", "burst")},
                    "weapon": {"targetLevel": 90, "importance": 1}} for key in characters}
    inp = PlannerInput(characters, targets, {"S": TierValue("S", "S", .9)},
                       {key: "S" for key in characters}, {}, set(), DEFAULT_PLANNER_CONFIG,
                       tier_scores={"YaeMiko": 90, "Furina": 70})
    signatures = []
    for quantity in (0, 10000000):
        altered = deepcopy(game)
        affected = 0
        for path, steps in altered.steps.items():
            replacements = []
            for step in steps:
                requirements = []
                for requirement in step.requirements:
                    material = altered.materials.get(requirement["material_key"])
                    if ((material and material.category == category)
                            or (category == "NORMAL_BOSS" and requirement["material_key"] == "$CHAR_BOSS")):
                        requirements.append({**requirement, "amount": quantity})
                        affected += 1
                    else:
                        requirements.append(requirement)
                replacements.append(replace(step, requirements=tuple(requirements)))
            altered.steps[path] = replacements
        assert affected > 0
        result = PlannerEngine().run(inp, generated_at="2026-09-28T00:00:00Z")
        assert len(result.global_plan) == len({goal.goal_key for goal in result.global_plan})
        output = GenerateTodayPlan(SimpleNamespace(now=lambda: datetime(2026, 9, 28, tzinfo=timezone.utc))).execute(
            result=result, game=altered,
            account=TodayAccountContext("ASIA", date(2026, 9, 28), "MONDAY", resin=0),
            availability=AvailabilityService(resin=0), context_hash=None)
        selection = select_today_task(quick_actions=output["quickActions"], farming=output["farming"],
            unavailable=output["unavailable"], blocked=output["blocked"], state=TodaySelectionState(),
            strategic_order=strategic_goal_order(result.global_plan), unresolved=result.unresolved,
            config_version="1", reorder_threshold=10)
        signatures.append(([(goal.goal_key, goal.final_score) for goal in result.global_plan],
                           selection.primary_task["primaryGoal"], selection.primary_task["score"]))
    assert signatures[0] == signatures[1]
