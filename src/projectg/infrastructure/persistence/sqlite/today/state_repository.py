"""Persistence mapping for Today hysteresis/pin state."""

from sqlalchemy.orm import Session

from projectg.domain.planning.today.selection import TodaySelectionState
from projectg.infrastructure.persistence.sqlite.models import TodayState


class TodayStateRepository:
    @staticmethod
    def load(db: Session, account_id: str) -> TodaySelectionState:
        row = db.get(TodayState, account_id)
        if row is None:
            return TodaySelectionState()
        return TodaySelectionState(
            pursued_task_id=row.pursued_task_id,
            pursued_character_key=row.pursued_character_key,
            pursued_score=row.pursued_score,
            ordering_group=row.ordering_group,
            pursued_config_version=row.pursued_config_version,
            pinned_character_key=row.pinned_character_key,
        )

    @staticmethod
    def save(db: Session, account_id: str, state: TodaySelectionState) -> TodaySelectionState:
        row = db.get(TodayState, account_id)
        if row is None:
            row = TodayState(account_id=account_id)
            db.add(row)
        row.pursued_task_id = state.pursued_task_id
        row.pursued_character_key = state.pursued_character_key
        row.pursued_score = state.pursued_score
        row.ordering_group = state.ordering_group
        row.pursued_config_version = state.pursued_config_version
        # Pin ownership is controlled by the planner-state use case. Selection
        # preserves it; writing it here keeps a single faithful state mapping.
        row.pinned_character_key = state.pinned_character_key
        return state
