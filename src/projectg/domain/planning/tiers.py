"""Tier score bands used by account-wide planning."""

BANDS = ((84, "S+"), (67, "S"), (50, "A"), (34, "B"), (17, "C"), (0, "D"))
ELIGIBLE_MINIMUMS = {"S+": 84, "S": 67, "A": 50, "B": 34, "C": 17, "D": 0}


def label_for(score: int | None) -> str:
    if score is None:
        return "Unranked"
    return next(label for low, label in BANDS if score >= low)


def investment_multiplier(score: int | None) -> float:
    """Discount low-tier component goals, independently of their required resources."""
    return {"C": 0.5, "D": 0.2}.get(label_for(score), 1.0)


LEGACY_DEFAULT_TIERS = (
    {"key": "T0", "label": "T0", "weight": 1.0, "order": 0},
    {"key": "T0_5", "label": "T0.5", "weight": 0.9, "order": 1},
    {"key": "T1", "label": "T1", "weight": 0.8, "order": 2},
    {"key": "T1_5", "label": "T1.5", "weight": 0.7, "order": 3},
    {"key": "T2", "label": "T2", "weight": 0.6, "order": 4},
    {"key": "T3", "label": "T3", "weight": 0.4, "order": 5},
)
