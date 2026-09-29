"""Reproducible per-piece artifact roll-value calculations from GOOD stats."""
from __future__ import annotations

from itertools import product
from math import isfinite
from typing import Any

FORMULA_VERSION = "artifact-rv-1"

# Highest five-star substat roll values, expressed in the units GOOD exports.
MAX_ROLL: dict[str, float] = {
    "hp": 298.75, "atk": 19.45, "def": 23.15,
    "hp_": 5.83, "atk_": 5.83, "def_": 7.29,
    "eleMas": 23.31, "enerRech_": 6.48,
    "critRate_": 3.89, "critDMG_": 7.77,
}
RARITY_ROLL_SCALE = {2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}
ROLL_QUALITY = (0.7, 0.8, 0.9, 1.0)


def _possible_roll_sums(key: str, rarity: int, cap: int) -> dict[int, set[float]]:
    maximum = MAX_ROLL[key] * RARITY_ROLL_SCALE[rarity]
    values = [maximum * quality for quality in ROLL_QUALITY]
    sums: dict[int, set[float]] = {0: {0.0}}
    for count in range(1, cap + 1):
        sums[count] = {subtotal + roll for subtotal in sums[count - 1] for roll in values}
    return sums


def _stat_value(row: Any) -> tuple[str, float] | None:
    if not isinstance(row, dict):
        return None
    key, value = row.get("key"), row.get("value")
    if not isinstance(key, str) or key not in MAX_ROLL or type(value) not in (int, float):
        return None
    number = float(value)
    if not isfinite(number) or number < 0:
        return None
    return key, number


def calculate_piece_rv(substats: list[dict[str, Any]], rarity: int, level: int) -> tuple[float | None, str]:
    """Return summed current RV (100% per max five-star roll), or UNKNOWN.

    GOOD substat displays can be rounded. Candidate roll totals within display
    precision are accepted; if they imply different RVs the result is unknown.
    """
    if rarity not in RARITY_ROLL_SCALE or type(level) is not int or not 0 <= level <= 20:
        return None, "UNKNOWN"
    if not isinstance(substats, list) or not 3 <= len(substats) <= 4:
        return None, "UNKNOWN"
    normalized = [_stat_value(row) for row in substats]
    if any(item is None for item in normalized):
        return None, "UNKNOWN"
    keys = [item[0] for item in normalized if item is not None]
    if len(keys) != len(set(keys)):
        return None, "UNKNOWN"

    total_rolls = min(9, len(substats) + level // 4)
    precision = 0.051
    states: dict[int, set[float]] = {0: {0.0}}
    for key, observed in (item for item in normalized if item is not None):
        max_value = MAX_ROLL[key]
        tolerance = precision if key.endswith("_") else 0.51
        sums_by_count = _possible_roll_sums(key, rarity, total_rolls)
        candidates = {count: [value / max_value * 100 for value in sums
                              if abs(value - observed) <= tolerance]
                      for count, sums in sums_by_count.items() if count > 0}
        candidates = {count: values for count, values in candidates.items() if values}
        if not candidates:
            return None, "UNKNOWN"
        updated: dict[int, set[float]] = {}
        for used, prior_values in states.items():
            for count, rv_values in candidates.items():
                combined_count = used + count
                if combined_count <= total_rolls:
                    updated.setdefault(combined_count, set()).update(
                        prior + value for prior in prior_values for value in rv_values)
        states = updated

    totals = states.get(total_rolls, set())
    if not totals or max(totals) - min(totals) > 0.11:
        return None, "UNKNOWN"
    return round(sum(totals) / len(totals), 2), "CALCULATED"
