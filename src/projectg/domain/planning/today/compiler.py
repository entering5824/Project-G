from hashlib import sha256
from projectg.domain.costs.models import CostStatus, ResolvedCost
from projectg.domain.game_catalog.models import GameData
from projectg.domain.planning.models import GoalType, GoalStatus, UpgradeGoal
from .availability import AvailabilityService
from .models import FarmSource, TaskType
from projectg.domain.planning.reasons import goal_explanation
from projectg.domain.planning.resource_policy import ResourcePolicy


class TaskCompiler:
    def __init__(self, game: GameData, availability: AvailabilityService | None = None):
        self.game = game
        self.availability = availability or AvailabilityService()

    def _domain_for(self, family: str | None, kind: str) -> tuple[str, str, str, int] | None:
        if not family:
            return None
        domains = [d for d in self.game.domains.values()
                   if d.type.upper() == kind and family in d.reward_material_families]
        if not domains:
            return None
        domain = sorted(domains, key=lambda d: d.key)[0]
        return domain.key, domain.schedule_group or "", domain.name or domain.key, domain.resin_cost

    def _farm_source(self, material_key: str) -> FarmSource | None:
        item = self.game.materials.get(material_key)
        if not item:
            return None
        source = item.source or {}
        kind = str(source.get('type', '')).upper()
        category = item.category.upper()
        family = item.family_key
        if category == 'CROWN' or kind == 'NON_FARMABLE':
            return FarmSource(TaskType.OBTAIN_RESOURCE, material_key, item.name, source)
        if category == 'TALENT_BOOK':
            domain = self._domain_for(family, 'TALENT')
            if domain:
                key, schedule, name, resin_cost = domain
                return FarmSource(TaskType.FARM_TALENT_DOMAIN, key, name, {'type': 'TALENT_DOMAIN', 'schedule_group': schedule, 'resin_cost': resin_cost, 'farm_notes': [f'Domain: {name}']})
            return None
        if category == 'WEAPON_ASCENSION':
            domain = self._domain_for(family, 'WEAPON')
            if domain:
                key, schedule, name, resin_cost = domain
                return FarmSource(TaskType.FARM_WEAPON_DOMAIN, key, name, {'type': 'WEAPON_DOMAIN', 'schedule_group': schedule, 'resin_cost': resin_cost, 'farm_notes': [f'Domain: {name}']})
            return None
        if category == 'WEEKLY_BOSS' or kind == 'WEEKLY_BOSS':
            boss_key = source.get('bossKey') or source.get('boss_key')
            boss = self.game.bosses.get(boss_key)
            details = {'type': 'WEEKLY_BOSS', 'weekly_limited': True, 'resin_cost': boss.resin_cost if boss else 30, 'resin_cost_after_discount': 60, 'farm_notes': [f'Weekly Trounce Domain: {boss.name}'] if boss and boss.name else []}
            return FarmSource(TaskType.FARM_WEEKLY_BOSS, boss_key, (boss.name if boss else boss_key) or item.name, details) if boss_key else None
        if category == 'NORMAL_BOSS' or kind == 'NORMAL_BOSS':
            boss_key = source.get('bossKey') or source.get('boss_key')
            boss = self.game.bosses.get(boss_key)
            details = {'type': 'NORMAL_BOSS', 'resin_cost': boss.resin_cost if boss else 40, 'farm_notes': [f'Normal Boss: {boss.name}'] if boss and boss.name else []}
            return FarmSource(TaskType.FARM_NORMAL_BOSS, boss_key, (boss.name if boss else boss_key) or item.name, details) if boss_key else None
        if category == 'MORA':
            return FarmSource(TaskType.FARM_MORA_LEYLINE, 'MoraLeyline', 'Mora Ley Line', {'type': 'LEY_LINE', 'resin_cost': 20, 'farm_notes': ['Blossom of Wealth']})
        if category == 'CHARACTER_EXP':
            return FarmSource(TaskType.FARM_EXP_LEYLINE, 'CharacterExpLeyline', 'Character EXP Ley Line', {'type': 'LEY_LINE', 'resin_cost': 20, 'farm_notes': ['Blossom of Revelation']})
        if category == 'WEAPON_EXP':
            if kind in {'LEY_LINE', 'FORGE_OR_LEY_LINE'}:
                return FarmSource(TaskType.FARM_WEAPON_EXP, 'WeaponEXPSource', 'Weapon EXP', {'type': 'FORGE_OR_LEY_LINE', 'resin_cost': 0, 'farm_notes': ['Forge Mystic Enhancement Ore (free materials) or farm Ley Line (20 Resin)']})
            return None
        if category == 'LOCAL_SPECIALTY' or kind == 'OPEN_WORLD':
            return FarmSource(TaskType.COLLECT_LOCAL_SPECIALTY, material_key, item.name, {'type': 'OPEN_WORLD', 'resin_cost': 0, 'farm_notes': list(source.get('sources') or [])})
        if category == 'ENEMY_DROP' or kind == 'ENEMY':
            family_sources = [m.source or {} for m in self.game.materials.values() if family and m.family_key == family]
            notes = list(dict.fromkeys((note for entry in family_sources for note in entry.get('sources') or [])))
            if not notes:
                notes = list(source.get('sources') or [])
            return FarmSource(TaskType.FARM_ENEMY_DROP, family or material_key, item.name, {'type': 'ENEMY', 'resin_cost': 0, 'farm_notes': notes})
        if kind in {'LEY_LINE'}:
            return FarmSource(TaskType.FARM_MORA_LEYLINE, material_key, item.name, source)
        return None

    @staticmethod
    def _task_id(task_type: TaskType, group_key: str) -> str:
        token = sha256(f"{task_type.value}:{group_key}".encode()).hexdigest()[:16]
        return f"today-{token}"

    def compile(self, ranked: list[tuple[UpgradeGoal, ResolvedCost]], *, game_date, server_region: str,
                unresolved: list[dict] | None = None):
        sections = {"quickActions": [], "farming": [], "unavailable": [], "blocked": []}
        issues = list(unresolved or [])
        for rank, (goal, cost) in enumerate(ranked, 1):
            methods = []
            availability = {"status": "AVAILABLE"}
            for key, amount in cost.required_cost.items():
                if amount <= 0:
                    continue
                descriptor = self._farm_source(key)
                material = self.game.materials.get(key)
                if descriptor:
                    method = {"type": descriptor.task_type.value, "materialKey": key, "amount": amount,
                              "source": {**descriptor.details, "key": descriptor.key, "name": descriptor.name},
                              "actionText": f"Farm/obtain {material.name if material else key}"}
                    methods.append(method)
                    if ResourcePolicy.for_goal_material(goal.type, material) == ResourcePolicy.TALENT_BOOK_AFFECTS_TODAY:
                        status = self.availability.is_available(method["source"], game_date, server_region)
                        if status["status"] == "UNAVAILABLE_TODAY":
                            availability = status
                else:
                    methods.append({"materialKey": key, "amount": amount,
                                    "actionText": f"Obtain {material.name if material else key}"})
            if goal.artifact_domain:
                methods.append({"type": "FARM_ARTIFACT_DOMAIN", "source": goal.artifact_domain,
                                "actionText": f"Farm {goal.artifact_domain.get('name') or goal.artifact_domain['key']}"})
            end = goal.strategic_target if goal.strategic_target is not None else goal.target_value
            title = f"{goal.character_key} — {goal.component_label} {goal.current_value} → {end}"
            action = "; ".join(dict.fromkeys(method["actionText"] for method in methods)) or "Progress toward this goal"
            task = {"id": self._task_id(TaskType.GOAL_ACTION, goal.goal_key), "type": "GOAL_ACTION",
                    "title": title, "character": {"key": goal.character_key}, "characterKeys": [goal.character_key],
                    "primaryGoal": {"goalKey": goal.goal_key, "characterKey": goal.character_key},
                    "parentGoalKeys": [goal.goal_key], "goalType": goal.type.value,
                    "rank": rank, "goalRank": rank, "score": round(goal.final_score, 2),
                    "current": {"value": goal.current_value}, "target": {"value": end},
                    "strategicTarget": {"value": end}, "requiredCost": dict(cost.required_cost),
                    "resourceInfo": cost.material_info, "actionText": action, "farmMethods": methods,
                    "whySummary": (goal.summary + (" · Mục tiêu bạn muốn build" if goal.planning_group == "PERSONAL"
                                     else " · Chuẩn bị Nhà Hát Imaginarium" if goal.planning_group == "THEATER" else "")),
                    "summary": goal.summary, "planningGroup": goal.planning_group,
                    "availability": availability["status"],
                    "availableToday": availability["status"] != "UNAVAILABLE_TODAY",
                    "availableWeekdays": availability.get("availableWeekdays", []),
                    "nextAvailableDate": availability.get("nextAvailableDate"),
                    "reasonCodes": list(goal.reason_codes), "goalExplanations": [goal_explanation(goal)],
                    "milestoneChain": [{"from": step.current, "to": step.target} for step in goal.milestone_chain]}
            if goal.status == GoalStatus.BLOCKED:
                task["blockedBy"] = list(goal.blocked_by)
                task["availability"] = "PREREQUISITE_BLOCKED"
                task["availableToday"] = False
                sections["blocked"].append(task)
            elif not task["availableToday"]:
                sections["unavailable"].append(task)
            else:
                sections["farming"].append(task)
            if cost.status == CostStatus.COST_DATA_MISSING:
                issues.append({"code": "COST_DATA_MISSING", "goalKey": goal.goal_key})
        return sections, issues
