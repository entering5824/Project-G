import json
from projectg.bootstrap.settings import settings

import pytest

from projectg.interface_adapters.mappers.snapshot import SnapshotValidationError, parse_snapshot
from projectg.interface_adapters.mappers.good_snapshot import snapshot_to_good
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.infrastructure.serialization.good_importer import GoodImporter


def sample():
    return {"version": 1, "characters": {"Mavuika": {
        "level": 90, "ascension": 6, "constellation": 0,
        "weapon": {"key": "A Thousand Blazing Suns", "level": 90},
        "talents": {"normal": 6, "skill": 9, "burst": 9},
        "artifacts": {"flower": {"setKey": "ObsidianCodex", "rv": 620},
                      "plume": {"setKey": "ObsidianCodex", "rv": 710},
                      "sands": {"setKey": "ObsidianCodex", "rv": 540},
                      "goblet": {"setKey": "OtherSet", "rv": 480},
                      "circlet": {"setKey": "ObsidianCodex", "rv": None}}}}}


def test_snapshot_derives_active_sets_and_keeps_unknown_rv_null():
    value = sample()
    value["characters"]["Mavuika"]["activeSets"] = [{"setKey": "Wrong", "pieces": 4}]
    normalized, report = parse_snapshot(value)
    char = normalized["characters"]["Mavuika"]
    assert char["activeSets"] == [{"setKey": "ObsidianCodex", "pieces": 4}]
    assert char["artifacts"]["circlet"]["rv"] is None
    assert any("activeSets differed" in warning for warning in report["warnings"])


def test_snapshot_adapter_roundtrips_through_good_normalizer_and_preserves_rv():
    raw, report = snapshot_to_good(sample(), get_game_data(settings))
    parsed = GoodImporter().parse(raw)
    normalized = GoodImporter().normalize(parsed)
    assert report["charactersImported"] == 1
    assert normalized.characters[0].key == "Mavuika"
    assert normalized.characters[0].talent_skill == 9
    assert len(normalized.artifacts) == 5
    by_slot = {item.slot_key: item for item in normalized.artifacts}
    assert by_slot["flower"].rv == 620
    assert by_slot["flower"].rv_status == "IMPORTED"
    assert by_slot["circlet"].rv is None


def test_snapshot_skips_bad_character_and_reports_missing_slots():
    value = sample()
    value["characters"]["Mavuika"]["level"] = 101
    value["characters"]["Furina"] = sample()["characters"]["Mavuika"]
    normalized, report = parse_snapshot(value)
    assert "Mavuika" not in normalized["characters"]
    assert report["unmapped"] == ["Mavuika"]
    assert report["charactersImported"] == 1
    value = sample()
    value["characters"]["Furina"] = sample()["characters"]["Mavuika"]
    value["characters"]["Furina"]["level"] = 101
    with pytest.raises(SnapshotValidationError):
        parse_snapshot({"version": 1, "characters": {"bad": value["characters"]["Furina"]}})
    value = sample()
    del value["characters"]["Mavuika"]["artifacts"]["circlet"]
    _, report = parse_snapshot(value)
    assert any("circlet" in warning for warning in report["warnings"])


def test_snapshot_preserves_character_level_95_and_100():
    value = sample()
    value["characters"]["Mavuika"]["level"] = 95
    normalized, _ = parse_snapshot(value)
    assert normalized["characters"]["Mavuika"]["level"] == 95
    value["characters"]["Mavuika"]["level"] = 100
    normalized, _ = parse_snapshot(value)
    assert normalized["characters"]["Mavuika"]["level"] == 100
