"""The only resource exception to goal-first Today availability."""
from enum import StrEnum

from projectg.domain.game_catalog.models import Material
from projectg.domain.planning.models import GoalType


class ResourcePolicy(StrEnum):
    INFORMATION_ONLY = "INFORMATION_ONLY"
    TALENT_BOOK_AFFECTS_TODAY = "TALENT_BOOK_AFFECTS_TODAY"

    @classmethod
    def for_goal_material(cls, goal_type: GoalType, material: Material | None) -> "ResourcePolicy":
        talents = {GoalType.TALENT_AUTO, GoalType.TALENT_SKILL, GoalType.TALENT_BURST}
        if goal_type in talents and material is not None and material.category.upper() == "TALENT_BOOK":
            return cls.TALENT_BOOK_AFFECTS_TODAY
        return cls.INFORMATION_ONLY
