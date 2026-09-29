"""Project stored tier pack data without interpreting scores or controls."""
from sqlalchemy.orm import Session
from projectg.application.ports.outbound.planner_gateway import PlannerTierPackFact
from projectg.infrastructure.persistence.sqlite.repositories.tier_pack import current_tier_pack


class PlannerTierReader:
    def __init__(self, db: Session):
        self._db = db

    def read(self, account_id: str) -> PlannerTierPackFact:
        pack = current_tier_pack(self._db, account_id)
        return PlannerTierPackFact(
            scores={key: row["score"] for key, row in pack["ratings"].items()
                    if row.get("score") is not None},
            controls=dict(pack["controls"]),
            minimum_tier_for_roadmap=pack["minimumTierForRoadmap"],
            selected_sets=dict(pack["selectedSets"]),
        )
