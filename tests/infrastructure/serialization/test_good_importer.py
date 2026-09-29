import json
import pytest
from projectg.infrastructure.serialization.good_importer import GoodImporter, GoodImportError

def test_valid_good_normalizes_expected_state(good_json):
    state = GoodImporter().normalize(good_json)
    assert len(state.characters) == 2 and len(state.weapons) == 3
    assert next(c for c in state.characters if c.key == "RaidenShogun").talent_burst == 10
    assert next(c for c in state.characters if c.key == "RaidenShogun").equipped_weapon_instance_id == "w1"
    assert len(state.artifacts) == 2 and state.teams[0].raw_config == {"conditional": True}

def test_rejects_non_good_format(good_json):
    good_json["format"] = "other"
    with pytest.raises(GoodImportError): GoodImporter().normalize(good_json)

def test_optional_sections_can_be_absent():
    state = GoodImporter().normalize({"format": "GOOD", "characters": []})
    assert state.weapons == state.artifacts == state.teams == []

def test_deterministic_canonical_hash(good_json):
    from projectg.infrastructure.serialization.good_document import canonical_state_hash
    imp = GoodImporter()
    assert canonical_state_hash(imp.normalize(good_json)) == canonical_state_hash(imp.normalize(json.loads(json.dumps(good_json))))

def test_good_teamchars_are_joined_through_loadout_data():
    good = {
        "format": "GOOD",
        "characters": [{"key": "Alpha", "level": 80}, {"key": "Beta", "level": 50}],
        "weapons": [], "artifacts": [],
        "teams": [{"id": "team_0", "name": "Test", "conditional": {"reaction": {"on": True}},
                   "loadoutData": [{"teamCharId": "teamchar_0"}, {"teamCharId": "teamchar_1"}]}],
        "teamchars": [{"id": "teamchar_0", "key": "Alpha", "conditional": {"Alpha": {"c1": "on"}},
                       "name": "Alpha Build"},
                      {"id": "teamchar_1", "key": "Beta", "conditional": {}, "name": "Beta Build"}],
    }
    team = GoodImporter().normalize(good).teams[0]
    assert team.members == ["Alpha", "Beta"]
    assert team.raw_config["conditional"] == {"reaction": {"on": True}}
    assert [x["id"] for x in team.raw_config["teamCharConfigs"]] == ["teamchar_0", "teamchar_1"]

def test_good_traveler_location_alias_links_to_only_owned_traveler():
    good = {"format": "GOOD", "characters": [{"key": "TravelerAnemo", "level": 90}],
            "weapons": [{"id": "traveler-weapon", "key": "ExaiphanesBlade", "level": 90,
                         "ascension": 6, "refinement": 1, "location": "Traveler"}],
            "artifacts": [{"id": "traveler-artifact", "location": "Traveler", "setKey": "Set",
                           "slotKey": "flower", "rarity": 5, "level": 20, "mainStatKey": "hp",
                           "substats": []}]}
    state = GoodImporter().normalize(good)
    assert state.weapons[0].location == "TravelerAnemo"
    assert state.characters[0].equipped_weapon_instance_id == "traveler-weapon"
    assert state.artifacts[0].character_key == "TravelerAnemo"

def test_owned_character_without_equipped_weapon_is_valid():
    state = GoodImporter().normalize({"format": "GOOD", "characters": [{"key": "Unarmed", "level": 20}], "weapons": []})
    assert state.characters[0].equipped_weapon_instance_id is None


def test_good_document_parser_discards_materials_before_hashing_and_storage(good_json):
    from projectg.infrastructure.serialization.good_document import GoodDocumentParser

    value = json.loads(json.dumps(good_json))
    value["materials"] = {"Mora": 123456}
    prepared = GoodDocumentParser(GoodImporter()).prepare(
        json.dumps(value).encode(), previous_effective_document=None)

    assert "materials" not in json.loads(prepared.raw_content)
    assert "materials" not in prepared.effective_document
    assert prepared.supplied_sections == frozenset({"characters", "weapons", "artifacts", "teams"})


def test_good_document_parser_merges_partial_export_before_normalizing(good_json):
    from projectg.infrastructure.serialization.good_document import GoodDocumentParser

    parser = GoodDocumentParser(GoodImporter())
    first = parser.prepare(json.dumps(good_json).encode(), previous_effective_document=None)
    partial = {
        "format": "GOOD",
        "characters": json.loads(json.dumps(good_json["characters"])),
    }
    partial["characters"][0]["level"] = 90

    merged = parser.prepare(
        json.dumps(partial).encode(),
        previous_effective_document=first.effective_document,
    )

    assert merged.supplied_sections == frozenset({"characters"})
    assert len(merged.state.weapons) == len(first.state.weapons)
    assert len(merged.state.artifacts) == len(first.state.artifacts)
    assert next(c for c in merged.state.characters if c.key == "RaidenShogun").level == 90


def test_good_document_parser_rejects_non_object_even_when_previous_snapshot_exists(good_json):
    from projectg.infrastructure.serialization.good_document import GoodDocumentParser

    parser = GoodDocumentParser(GoodImporter())
    first = parser.prepare(json.dumps(good_json).encode(), previous_effective_document=None)

    with pytest.raises(GoodImportError):
        parser.prepare(b"[]", previous_effective_document=first.effective_document)


@pytest.mark.parametrize("level", [95, 100])
def test_import_preserves_character_levels_above_90(level):
    state = GoodImporter().normalize({"format": "GOOD", "characters": [{"key": "Mavuika", "level": level}]})
    assert state.characters[0].level == level


def test_import_rejects_character_level_above_100():
    with pytest.raises(GoodImportError):
        GoodImporter().normalize({"format": "GOOD", "characters": [{"key": "Mavuika", "level": 101}]})
