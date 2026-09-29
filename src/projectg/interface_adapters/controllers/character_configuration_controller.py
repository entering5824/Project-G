"""Translate character configuration actions to desktop payloads."""

from projectg.application.use_cases.characters.get_configuration import GetCharacterConfiguration
from projectg.application.use_cases.characters.save_configuration import (
    SaveCharacterConfiguration,
    SaveCharacterConfigurationRequest,
)


class CharacterConfigurationController:
    def __init__(self, get_configuration: GetCharacterConfiguration,
                 save_configuration: SaveCharacterConfiguration):
        self._get_configuration = get_configuration
        self._save_configuration = save_configuration

    def load(self, character_key: str) -> dict:
        return _payload(self._get_configuration.execute(character_key))

    def save(self, character_key: str, *, tier_key: str | None,
             priority_override: str) -> dict:
        request = SaveCharacterConfigurationRequest(character_key, tier_key, priority_override)
        return _payload(self._save_configuration.execute(request))


def _payload(value) -> dict:
    return {
        "characterKey": value.character_key,
        "tierConfigVersion": value.tier_config_version,
        "tiers": list(value.tiers),
        "tierKey": value.tier_key,
        "tierAssignmentVersion": value.tier_assignment_version,
        "priorityOverride": value.priority_override,
        "activePresetKey": value.active_preset_key,
        "presets": list(value.presets),
    }
