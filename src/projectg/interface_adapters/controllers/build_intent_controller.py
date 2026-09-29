"""Translate desktop build intent controls to persistence operations."""


class BuildIntentController:
    def __init__(self, gateway):
        self._gateway = gateway

    def load(self) -> dict:
        return self._gateway.load()

    def set_personal_state(self, character_key: str, state: str) -> dict:
        return self._gateway.save_personal(character_key, state)

    def save_theater(self, config: dict) -> dict:
        return self._gateway.save_theater(config)
