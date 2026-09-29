"""Translate TierPack JSON files to and from application values."""

import json
from typing import Any


def decode_tier_pack(content: bytes) -> dict[str, Any]:
    value = json.loads(content.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("TierPack file must contain a JSON object.")
    return value


def encode_tier_pack(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
