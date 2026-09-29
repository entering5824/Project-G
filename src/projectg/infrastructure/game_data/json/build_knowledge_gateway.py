"""Configured local build-knowledge adapter."""

from projectg.infrastructure.configuration.settings import Settings
from projectg.application.ports.outbound.build_knowledge_gateway import BuildKnowledgePack
from projectg.infrastructure.game_data.json.build_profiles import load_build_pack


class LocalBuildKnowledgeGateway:
    def __init__(self, configuration: Settings):
        self._configuration = configuration

    def load(self, character_keys: set[str]) -> BuildKnowledgePack:
        return load_build_pack(
            self._configuration.build_profiles_path, character_keys=character_keys
        )
