"""Translate tier pack actions and file operations for desktop presentation."""

from projectg.application.ports.outbound.file_storage import FileStorage
from projectg.application.use_cases.tier_packs.get_tier_pack import GetTierPack
from projectg.application.use_cases.tier_packs.requests import SaveTierPackRequest, ValidateTierPackRequest
from projectg.application.use_cases.tier_packs.save_tier_pack import SaveTierPack
from projectg.application.use_cases.tier_packs.validate_tier_pack import ValidateTierPack
from projectg.interface_adapters.mappers.tier_pack_json import decode_tier_pack, encode_tier_pack


class TierPackController:
    def __init__(self, get_pack: GetTierPack, save_pack: SaveTierPack,
                 validate_pack: ValidateTierPack, storage: FileStorage):
        self._get_pack, self._save_pack = get_pack, save_pack
        self._validate_pack, self._storage = validate_pack, storage

    def load(self) -> dict:
        return self._get_pack.execute().values

    def save(self, payload: dict) -> dict:
        return self._save_pack.execute(SaveTierPackRequest(payload)).values

    def validate(self, payload: dict) -> dict:
        return self._validate_pack.execute(ValidateTierPackRequest(payload)).values

    def import_file(self, key: str) -> dict:
        payload = decode_tier_pack(self._storage.read(key))
        normalized = self.validate(payload)
        return self.save(normalized)

    def export_file(self, key: str, payload: dict) -> None:
        normalized = self.validate(payload)
        self._storage.write(key, encode_tier_pack(normalized))
