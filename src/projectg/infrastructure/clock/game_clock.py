from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo


REGION_TIMEZONES = {
    "ASIA": "Asia/Shanghai",
    "EUROPE": "Europe/Paris",
    "AMERICA": "America/New_York",
    "TW_HK_MO": "Asia/Hong_Kong",
}


@dataclass(frozen=True)
class GameTime:
    server_region: str
    local_now: datetime
    game_date: date
    weekday: str


class GameClock:
    """Genshin server-local clock. The in-game day rolls over at 04:00 local time."""

    def now(self, server_region: str, instant: datetime | None = None) -> GameTime:
        region = (server_region or "ASIA").upper()
        zone_name = REGION_TIMEZONES.get(region)
        if not zone_name:
            raise ValueError(f"Unsupported server region: {server_region}")
        value = instant or datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        local = value.astimezone(ZoneInfo(zone_name))
        game_day = (local - timedelta(hours=4)).date()
        return GameTime(region, local, game_day, game_day.strftime("%A").upper())
