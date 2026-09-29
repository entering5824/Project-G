"""Application projection policy for tier-pack editing."""

from typing import Any

from projectg.application.ports.outbound.tier_pack_gateway import TierPackContext
from projectg.domain.planning.tiers import label_for


def build_tier_pack_view(context: TierPackContext) -> dict[str, Any]:
    pack = context.pack
    rows = [
        {
            "characterKey": key,
            "score": pack["ratings"].get(key, {}).get("score"),
            "notes": pack["ratings"].get(key, {}).get("notes", ""),
            "tier": label_for(pack["ratings"].get(key, {}).get("score")),
            "owned": key in context.owned_characters,
            "control": pack["controls"].get(key, "NORMAL"),
            "selectedSet": pack["selectedSets"].get(key),
            "setOptions": list(context.set_options.get(key, ())),
        }
        for key in sorted(context.character_keys)
    ]
    return {"pack": pack, "rows": rows, "hash": context.pack_hash}
