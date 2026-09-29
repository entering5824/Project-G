"""Target domain validation and preset policies."""

from .presets import TargetPresetViolation, next_preset_key
from .rules import TargetRuleViolation, validate_target_rules
from .validation import TargetValidationViolation, validate_target

__all__ = [
    "TargetPresetViolation",
    "TargetRuleViolation",
    "TargetValidationViolation",
    "next_preset_key",
    "validate_target_rules",
    "validate_target",
]
