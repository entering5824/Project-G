"""Read persisted account facts needed to compile a Today plan."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import Account


@dataclass(frozen=True)
class TodayAccountFacts:
    account_id: str
    current_snapshot_id: str | None
    server_region: str
    game_language: str
    world_level: int | None
    resin: int | None
    weekly_claimed: tuple[str, ...]
    unavailable_sources: tuple[str, ...]


class TodayContextReader:
    def __init__(self, configuration: Settings):
        self._configuration = configuration

    def account(self, db: Session) -> TodayAccountFacts | None:
        row = db.get(Account, self._configuration.account_id)
        if row is None:
            return None
        return TodayAccountFacts(
            account_id=row.id,
            current_snapshot_id=row.current_snapshot_id,
            server_region=row.server_region,
            game_language=row.game_language or "en",
            world_level=row.world_level,
            resin=row.resin,
            weekly_claimed=tuple(row.weekly_claimed_json or ()),
            unavailable_sources=tuple(row.unavailable_sources_json or ()),
        )
