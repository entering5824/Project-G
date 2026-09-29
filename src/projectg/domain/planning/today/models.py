from dataclasses import dataclass
from enum import StrEnum


class TaskType(StrEnum):
    GOAL_ACTION = "GOAL_ACTION"
    FARM_TALENT_DOMAIN = "FARM_TALENT_DOMAIN"
    FARM_WEAPON_DOMAIN = "FARM_WEAPON_DOMAIN"
    FARM_NORMAL_BOSS = "FARM_NORMAL_BOSS"
    FARM_WEEKLY_BOSS = "FARM_WEEKLY_BOSS"
    FARM_MORA_LEYLINE = "FARM_MORA_LEYLINE"
    FARM_EXP_LEYLINE = "FARM_EXP_LEYLINE"
    FARM_WEAPON_EXP = "FARM_WEAPON_EXP"
    COLLECT_LOCAL_SPECIALTY = "COLLECT_LOCAL_SPECIALTY"
    FARM_ENEMY_DROP = "FARM_ENEMY_DROP"
    OBTAIN_RESOURCE = "OBTAIN_RESOURCE"
    FARM_ARTIFACT_DOMAIN = "FARM_ARTIFACT_DOMAIN"  # Reserved; not compiled.


@dataclass(frozen=True)
class FarmSource:
    task_type: TaskType
    key: str
    name: str
    details: dict
