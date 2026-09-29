"""Read the installed tier pack and its application projection."""

from projectg.application.ports.outbound.tier_pack_gateway import TierPackData, TierPackGateway
from projectg.application.tier_packs.policy import build_tier_pack_view


class GetTierPack:
    def __init__(self, gateway: TierPackGateway):
        self._gateway = gateway

    def execute(self) -> TierPackData:
        return TierPackData(build_tier_pack_view(self._gateway.load_context()))
