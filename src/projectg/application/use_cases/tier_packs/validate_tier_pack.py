"""Validate a candidate tier pack without saving it."""

from projectg.application.ports.outbound.tier_pack_gateway import TierPackData, TierPackGateway
from projectg.application.use_cases.tier_packs.requests import ValidateTierPackRequest
from projectg.domain.planning.tier_pack import validate_tier_pack


class ValidateTierPack:
    def __init__(self, gateway: TierPackGateway):
        self._gateway = gateway

    def execute(self, request: ValidateTierPackRequest) -> TierPackData:
        context = self._gateway.load_context()
        return TierPackData(validate_tier_pack(
            request.payload,
            known_keys=set(context.character_keys),
            known_sets=set(context.artifact_set_keys),
        ))
