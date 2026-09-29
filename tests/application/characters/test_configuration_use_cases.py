import pytest

from projectg.application.ports.outbound.character_configuration_gateway import (
    CharacterConfigurationContext,
    CharacterConfigurationData,
)
from projectg.application.use_cases.characters.get_configuration import GetCharacterConfiguration
from projectg.application.use_cases.characters.save_configuration import (
    SaveCharacterConfiguration,
    SaveCharacterConfigurationRequest,
)


class FakeGateway:
    def __init__(self, *, owned=True):
        self.owned = owned
        self.committed = None
        self.data = CharacterConfigurationData(
            "Amber",
            2,
            ({"key": "T1"}, {"key": "T2"}),
            "T1",
            3,
            "NORMAL",
            "default",
            (),
        )

    def load_context(self, character_key):
        data = CharacterConfigurationData(
            character_key,
            self.data.tier_config_version,
            self.data.tiers,
            self.data.tier_key,
            self.data.tier_assignment_version,
            self.data.priority_override,
            self.data.active_preset_key,
            self.data.presets,
        )
        return CharacterConfigurationContext(self.owned, data)

    def commit_validated(self, character_key, *, tier_key, priority_override):
        self.committed = (character_key, tier_key, priority_override)
        return CharacterConfigurationData(
            character_key, 2, self.data.tiers, tier_key, 4,
            priority_override, "default", (),
        )


def test_get_configuration_uses_character_context_as_query():
    configuration = GetCharacterConfiguration(FakeGateway()).execute("Amber")

    assert configuration.character_key == "Amber"
    assert configuration.tier_key == "T1"


def test_save_configuration_validates_before_committing_to_gateway():
    gateway = FakeGateway()
    request = SaveCharacterConfigurationRequest("Amber", "T2", "PRIORITIZED")

    result = SaveCharacterConfiguration(gateway).execute(request)

    assert gateway.committed == ("Amber", "T2", "PRIORITIZED")
    assert result.priority_override == "PRIORITIZED"


def test_save_configuration_rejects_invalid_tier_without_persistence_call():
    gateway = FakeGateway()

    with pytest.raises(ValueError, match="Tier key"):
        SaveCharacterConfiguration(gateway).execute(
            SaveCharacterConfigurationRequest("Amber", "T9", "NORMAL")
        )

    assert gateway.committed is None


def test_character_configuration_rejects_unowned_character_in_application():
    gateway = FakeGateway(owned=False)

    with pytest.raises(ValueError, match="not owned"):
        GetCharacterConfiguration(gateway).execute("Amber")
