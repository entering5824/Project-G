from collections import defaultdict

from projectg.domain.costs.models import CostStatus
from projectg.domain.costs.resolver import resolve_cost, resolve_requirements
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.models import GoalType

PLANNING_WINDOW = 10


class CostEngine:
    """Pure progression-cost policy over domain goals and immutable game catalog data."""

    def __init__(self, game_data: GameData):
        self.game = game_data

    def _requirements(self, goal, value: int):
        return resolve_requirements(self.game, goal, value)

    def _weapon_target_exceeds_cap(self, goal) -> bool:
        if goal.type != GoalType.WEAPON_LEVEL or not goal.weapon_key:
            return False
        weapon = self.game.weapons.get(goal.weapon_key)
        return bool(weapon and int(goal.target_value) > weapon.max_level)

    def _weapon_ascension_available(self, goal) -> bool:
        return bool(
            goal.type == GoalType.WEAPON_LEVEL
            and goal.weapon_key
            and f"weapon_ascension:{goal.weapon_key}" in self.game.steps
        )

    def cost_for_goal(self, goal) -> dict:
        if goal.type == GoalType.ARTIFACT_QUALITY:
            return {
                "costStatus": "RNG_HEAVY",
                "fullCost": None,
                "nextMilestoneCost": None,
                "costWarning": "ARTIFACT_COST_IS_NON_DETERMINISTIC",
            }

        full_req = self._requirements(goal, int(goal.target_value))
        next_value = goal.next_milestone if goal.next_milestone is not None else goal.target_value
        next_req = self._requirements(goal, int(next_value))
        full = resolve_cost(self.game, full_req)
        milestone = resolve_cost(self.game, next_req)

        target_exceeds_cap = self._weapon_target_exceeds_cap(goal)
        if target_exceeds_cap:
            full.flags = [flag for flag in full.flags if flag != "GAME_DATA_MISSING"]
            full.flags.append("TARGET_ABOVE_WEAPON_CAP")

        weapon_ascension_missing = (
            goal.type == GoalType.WEAPON_LEVEL
            and int(goal.target_value) > 20
            and not self._weapon_ascension_available(goal)
        )
        if weapon_ascension_missing and full_req is not None:
            full.status = CostStatus.COST_DATA_MISSING
            full.flags.append("WEAPON_ASCENSION_COST_DATA_MISSING")

        if (
            goal.type == GoalType.WEAPON_LEVEL
            and int(next_value) > 20
            and not self._weapon_ascension_available(goal)
            and next_req is not None
        ):
            milestone.status = CostStatus.COST_DATA_MISSING
            milestone.flags.append("WEAPON_ASCENSION_COST_DATA_MISSING")

        warning = None
        if full_req is None:
            warning = "GAME_DATA_MISSING"
        elif target_exceeds_cap:
            warning = "TARGET_ABOVE_WEAPON_CAP"
        elif weapon_ascension_missing:
            warning = "WEAPON_ASCENSION_COST_DATA_MISSING"

        return {
            "costStatus": full.status.value,
            "fullCost": full.to_dict(),
            "nextMilestoneCost": milestone.to_dict(),
            "costWarning": warning,
        }

    def enrich_plan(self, plan_dict: dict, goals: list) -> dict:
        if self.game.error:
            plan_dict.setdefault("unresolved", []).append(
                {
                    "code": "GAME_DATA_MISSING",
                    "characterKey": None,
                    "severity": "warning",
                    "message": "Local GameData could not be loaded.",
                    "details": self.game.error,
                }
            )
            return plan_dict

        for goal in goals:
            cost = self.cost_for_goal(goal)
            for action in plan_dict.get("global", []):
                if action["id"] == goal.id:
                    action.update(cost)
                    break

        missing_keys = {
            goal.character_key
            for goal in goals
            if goal.type != GoalType.ARTIFACT_QUALITY
            and self._requirements(goal, int(goal.target_value)) is None
        }
        for key in sorted(missing_keys):
            matching = [
                goal
                for goal in goals
                if goal.character_key == key
                and self._requirements(goal, int(goal.target_value)) is None
            ]
            if matching and all(self._weapon_target_exceeds_cap(goal) for goal in matching):
                continue
            plan_dict.setdefault("unresolved", []).append(
                {
                    "code": "GAME_DATA_MISSING",
                    "characterKey": key,
                    "severity": "warning",
                    "message": "Cost data is unavailable for this goal; strategic planner goal is retained.",
                    "details": {},
                }
            )

        for goal in goals:
            if self._weapon_target_exceeds_cap(goal):
                plan_dict.setdefault("unresolved", []).append(
                    {
                        "code": "INVALID_UPGRADE_TARGET",
                        "characterKey": goal.character_key,
                        "severity": "warning",
                        "message": "Configured weapon target exceeds its maximum level in local GameData.",
                        "details": {
                            "goalKey": goal.goal_key,
                            "weaponKey": goal.weapon_key,
                            "maxLevel": self.game.weapons[goal.weapon_key].max_level,
                            "targetLevel": goal.target_value,
                        },
                    }
                )

        plan_dict["gameData"] = {
            "schemaVersion": self.game.metadata.get("schema_version"),
            "gameVersion": self.game.metadata.get("game_version"),
            "dataVersion": self.game.metadata.get("data_version"),
        }
        return plan_dict

    def enrich_action_detail(self, detail: dict, goal) -> dict:
        cost = self.cost_for_goal(goal)
        detail.update(cost)
        detail["action"].update(cost)
        return detail

    def required_materials(self, goals: list, limit: int = PLANNING_WINDOW) -> dict:
        aggregated: dict[str, int] = defaultdict(int)
        needed_by: dict[str, set[str]] = defaultdict(set)
        unresolved = []

        for goal in goals[:limit]:
            if goal.type == GoalType.ARTIFACT_QUALITY:
                continue
            requirements = self._requirements(goal, int(goal.target_value))
            if requirements is None:
                unresolved.append(
                    {
                        "code": (
                            "INVALID_UPGRADE_TARGET"
                            if self._weapon_target_exceeds_cap(goal)
                            else "COST_DATA_MISSING"
                        ),
                        "characterKey": goal.character_key,
                        "goalKey": goal.goal_key,
                    }
                )
                continue
            if (
                goal.type == GoalType.WEAPON_LEVEL
                and int(goal.target_value) > 20
                and not self._weapon_ascension_available(goal)
            ):
                unresolved.append(
                    {
                        "code": "COST_DATA_MISSING",
                        "characterKey": goal.character_key,
                        "goalKey": goal.goal_key,
                        "component": "WEAPON_ASCENSION",
                    }
                )
            for key, amount in requirements.items():
                aggregated[key] += amount
                needed_by[key].add(goal.character_key)

        rows = [
            {
                "materialKey": key,
                "name": self.game.materials[key].name,
                "category": self.game.materials[key].category,
                "required": amount,
                "neededBy": sorted(needed_by[key]),
                "source": self.game.materials[key].source or {},
            }
            for key, amount in sorted(aggregated.items())
        ]
        return {
            "planningWindow": min(limit, len(goals)),
            "items": rows,
            "unresolved": unresolved,
            "gameData": {
                "dataVersion": self.game.metadata.get("data_version"),
                "error": self.game.error,
            },
        }
