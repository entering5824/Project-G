"""Pure business rules for character progression targets."""


class TargetRuleViolation(ValueError):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.message = message
        self.field = field


def validate_target_rules(target: dict) -> None:
    """Reject progression targets that cannot be reached in the game."""
    level, ascension = target["level"], target["ascension"]
    if not 1 <= level <= 90:
        raise TargetRuleViolation("Level target must be between 1 and 90.", "level")
    if not 0 <= ascension <= 6:
        raise TargetRuleViolation("Ascension target must be between 0 and 6.", "ascension")
    minimum_levels = (1, 20, 40, 50, 60, 70, 80)
    maximum_levels = (20, 40, 50, 60, 70, 80, 90)
    if not minimum_levels[ascension] <= level <= maximum_levels[ascension]:
        raise TargetRuleViolation("Level target is impossible for this ascension target.", "level")

    talent_maximums = (1, 2, 4, 6, 8, 10, 13)
    for name in ("normal", "skill", "burst"):
        talent = target["talents"][name]
        if not 1 <= talent["target"] <= 13:
            raise TargetRuleViolation("Talent target must be between 1 and 13.", f"talents.{name}.target")
        if not 0 <= talent["importance"] <= 1:
            raise TargetRuleViolation("Importance must be between 0 and 1.", f"talents.{name}.importance")
        if talent["enabled"] and talent["target"] > talent_maximums[ascension]:
            raise TargetRuleViolation("Talent target is impossible for this ascension target.",
                                      f"talents.{name}.target")

    if not 1 <= target["weapon"]["targetLevel"] <= 90:
        raise TargetRuleViolation("Weapon level target must be between 1 and 90.", "weapon.targetLevel")

    for field, amount in (
        ("importance.level", target["importance"]["level"]),
        ("importance.ascension", target["importance"]["ascension"]),
        ("weapon.importance", target["weapon"]["importance"]),
        ("artifact.importance", target["artifact"]["importance"]),
    ):
        if not 0 <= amount <= 1:
            raise TargetRuleViolation("Importance must be between 0 and 1.", field)

    gate = target["artifact"].get("gate") or {}
    for key, maximum in (("minLevel", 90), ("minAscension", 6), ("weaponMinLevel", 90)):
        amount = gate.get(key)
        minimum = 0 if key == "minAscension" else 1
        if amount is not None and not minimum <= amount <= maximum:
            raise TargetRuleViolation("Artifact gate value is out of range.", f"artifact.gate.{key}")
    required = gate.get("requiredTalents") or []
    if len(set(required)) != len(required):
        raise TargetRuleViolation("requiredTalents must be unique.", "artifact.gate.requiredTalents")
    if any(not target["talents"][name]["enabled"] for name in required):
        raise TargetRuleViolation("A required artifact gate talent must be enabled in the target.",
                                  "artifact.gate.requiredTalents")
