"""Small immutable reference and boundary operations used by desktop forms."""

from projectg.domain.planning.tiers import ELIGIBLE_MINIMUMS, label_for
from projectg.interface_adapters.mappers.snapshot import parse_snapshot
from projectg.interface_adapters.mappers.target_contract import target_contract_bundle

def score_for_tier(tier: str) -> int:
    """Return the minimum score that represents a selected tier."""
    return ELIGIBLE_MINIMUMS[tier]


__all__ = ["label_for", "score_for_tier", "parse_snapshot", "target_contract_bundle"]
