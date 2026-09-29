"""Policies for stable target-preset identifiers."""

from __future__ import annotations

import re
import unicodedata


class TargetPresetViolation(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.message = message
        self.field = field


def next_preset_key(label: object, occupied: set[str] | frozenset[str]) -> tuple[str, str]:
    """Return the normalized label and the first collision-free preset key."""
    normalized_label = str(label).strip()
    if not normalized_label:
        raise TargetPresetViolation("Preset label cannot be blank.", "label")

    base = (
        unicodedata.normalize("NFKD", normalized_label)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:48] or "build"
    preset_key = base
    suffix = 2
    while preset_key in occupied:
        ending = f"-{suffix}"
        preset_key = f"{base[:48-len(ending)]}{ending}"
        suffix += 1
    return normalized_label, preset_key
