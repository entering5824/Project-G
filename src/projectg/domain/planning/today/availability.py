from datetime import date, timedelta
from enum import StrEnum


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_TODAY = "UNAVAILABLE_TODAY"
    ALWAYS_AVAILABLE = "ALWAYS_AVAILABLE"
    WEEKLY_LIMITED = "WEEKLY_LIMITED"


DAY_GROUPS = {
    "MON_THU": {"MONDAY", "THURSDAY"},
    "MON_THU_SUN": {"MONDAY", "THURSDAY"},
    "TUE_FRI": {"TUESDAY", "FRIDAY"},
    "WED_SAT": {"WEDNESDAY", "SATURDAY"},
    "DAILY": {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"},
}


class AvailabilityService:
    def __init__(self, clock: object | None = None, *, resin: int | None = None,
                 weekly_claimed: set[str] | None = None,
                 weekly_claim_count: int | None = None,
                 unavailable_sources: set[str] | None = None):
        # Kept as a compatibility argument; availability uses the explicit
        # game_date passed to is_available and never reads the host clock.
        self.resin = resin
        self.weekly_claimed = weekly_claimed or set()
        self.weekly_claim_count = len(self.weekly_claimed) if weekly_claim_count is None else weekly_claim_count
        self.unavailable_sources = unavailable_sources or set()

    def is_available(self, source: dict | None, game_date: date, server_region: str) -> dict:
        source = source or {}
        kind = str(source.get("type", "")).upper()
        source_key = str(source.get("key") or "")
        if source_key and source_key in self.unavailable_sources:
            return {"status": AvailabilityStatus.UNAVAILABLE_TODAY.value,
                    "availableWeekdays": [], "nextAvailableDate": None,
                    "warning": "SOURCE_TEMPORARILY_UNAVAILABLE"}
        if source_key and source_key in self.weekly_claimed:
            return {"status": AvailabilityStatus.UNAVAILABLE_TODAY.value,
                    "availableWeekdays": [], "nextAvailableDate": None,
                    "warning": "WEEKLY_REWARD_ALREADY_CLAIMED"}
        resin_kinds = {"WEEKLY_BOSS", "NORMAL_BOSS", "LEY_LINE", "TALENT_DOMAIN",
                       "WEAPON_DOMAIN", "ARTIFACT_DOMAIN", "DOMAIN"}
        resin_cost = source.get("resin_cost")
        if kind == "WEEKLY_BOSS" and resin_cost is not None:
            # The first three Trounce Domain rewards each week cost 30; further
            # claims cost 60. weekly_claimed stores the claimed source keys.
            resin_cost = int(resin_cost if self.weekly_claim_count < 3
                             else source.get("resin_cost_after_discount", resin_cost))
        if resin_cost is None and kind in {"TALENT_DOMAIN", "WEAPON_DOMAIN", "ARTIFACT_DOMAIN", "DOMAIN", "LEY_LINE"}:
            resin_cost = 20
        if resin_cost is None and kind == "NORMAL_BOSS":
            resin_cost = 40
        scheduled = kind in {"TALENT_DOMAIN", "WEAPON_DOMAIN", "ARTIFACT_DOMAIN", "DOMAIN"}
        weekdays = []
        next_date = None
        if scheduled:
            group = str(source.get("schedule_group") or source.get("scheduleGroup") or "").upper()
            days = DAY_GROUPS.get(group)
            if days:
                available_days = days | {"SUNDAY"}
                order = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"]
                weekdays = sorted(available_days, key=order.index)
                next_date = game_date.isoformat()
                if game_date.strftime("%A").upper() not in available_days:
                    candidate = game_date + timedelta(days=1)
                    for _ in range(7):
                        if candidate.strftime("%A").upper() in available_days:
                            next_date = candidate.isoformat()
                            break
                        candidate += timedelta(days=1)
        if kind in resin_kinds and self.resin is not None and self.resin < int(resin_cost or 0):
            return {"status": AvailabilityStatus.UNAVAILABLE_TODAY.value,
                    "availableWeekdays": weekdays, "nextAvailableDate": next_date,
                    "warning": "INSUFFICIENT_RESIN", "resinCost": int(resin_cost or 0),
                    "resinAvailable": self.resin}
        if kind in {"WEEKLY_BOSS"} or source.get("weekly_limited"):
            return {"status": AvailabilityStatus.WEEKLY_LIMITED.value, "availableWeekdays": [], "nextAvailableDate": None,
                    "resinCost": int(resin_cost or 0) if resin_cost is not None else None,
                    "resinAvailable": self.resin}
        if kind in {"NORMAL_BOSS", "LEY_LINE", "OPEN_WORLD", "ENEMY", "FORGE_OR_LEY_LINE", "NON_FARMABLE"}:
            return {"status": AvailabilityStatus.ALWAYS_AVAILABLE.value, "availableWeekdays": [], "nextAvailableDate": None,
                    "resinCost": int(resin_cost or 0) if resin_cost is not None else 0,
                    "resinAvailable": self.resin}
        if kind not in {"TALENT_DOMAIN", "WEAPON_DOMAIN", "ARTIFACT_DOMAIN", "DOMAIN"}:
            return {"status": AvailabilityStatus.ALWAYS_AVAILABLE.value, "availableWeekdays": [], "nextAvailableDate": None}
        group = str(source.get("schedule_group") or source.get("scheduleGroup") or "").upper()
        days = DAY_GROUPS.get(group)
        if days is None:
            return {"status": AvailabilityStatus.UNAVAILABLE_TODAY.value, "availableWeekdays": [], "nextAvailableDate": None,
                    "warning": "DOMAIN_SCHEDULE_MISSING"}
        # Sunday follows the game's schedule: every domain reward family is available.
        available_days = days | {"SUNDAY"}
        today = game_date.strftime("%A").upper()
        if today in available_days:
            return {"status": AvailabilityStatus.AVAILABLE.value,
                    "availableWeekdays": sorted(available_days, key=lambda d: ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"].index(d)),
                    "nextAvailableDate": game_date.isoformat(), "resinCost": int(resin_cost or 20),
                    "resinAvailable": self.resin}
        next_day = game_date + timedelta(days=1)
        for _ in range(7):
            if next_day.strftime("%A").upper() in available_days:
                break
            next_day += timedelta(days=1)
        return {"status": AvailabilityStatus.UNAVAILABLE_TODAY.value,
                "availableWeekdays": sorted(available_days, key=lambda d: ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"].index(d)),
                "nextAvailableDate": next_day.isoformat(), "resinCost": int(resin_cost or 20),
                "resinAvailable": self.resin}
