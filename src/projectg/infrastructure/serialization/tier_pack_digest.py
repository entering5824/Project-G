"""Canonical JSON digest for persisted tier-pack content."""

import hashlib
import json
from typing import Any

from projectg.domain.planning.tier_pack import tier_pack_content


def tier_pack_hash(pack: dict[str, Any]) -> str:
    encoded = json.dumps(
        tier_pack_content(pack),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
