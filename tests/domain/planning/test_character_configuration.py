import pytest

from projectg.domain.planning.character_configuration import validate_character_configuration


def test_character_configuration_accepts_configured_tier_and_priority():
    validate_character_configuration(
        owned=True,
        tiers=({"key": "T1"}, {"key": "T2"}),
        tier_key="T2",
        priority_override="PRIORITIZED",
    )


def test_character_configuration_rejects_unowned_and_unknown_priority():
    with pytest.raises(ValueError, match="not owned"):
        validate_character_configuration(
            owned=False, tiers=(), tier_key=None, priority_override="NORMAL"
        )
    with pytest.raises(ValueError, match="Invalid priority"):
        validate_character_configuration(
            owned=True, tiers=(), tier_key=None, priority_override="FAST"
        )
