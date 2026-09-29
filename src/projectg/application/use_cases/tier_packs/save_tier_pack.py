"""Validate and save a tier pack."""

from projectg.application.ports.outbound.tier_pack_gateway import TierPackData, TierPackGateway
from projectg.application.use_cases.tier_packs.requests import SaveTierPackRequest
from projectg.domain.planning.tier_pack import tier_pack_content, validate_tier_pack


class SaveTierPack:
    def __init__(self, gateway: TierPackGateway):
        self._gateway = gateway

    def execute(self, request: SaveTierPackRequest) -> TierPackData:
        context = self._gateway.load_context()
        normalized = validate_tier_pack(
            request.payload,
            known_keys=set(context.character_keys),
            known_sets=set(context.artifact_set_keys),
        )
        if tier_pack_content(context.pack) == normalized:
            return TierPackData(context.pack)
        return TierPackData(self._gateway.commit_validated(normalized))
