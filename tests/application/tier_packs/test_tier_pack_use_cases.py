from projectg.application.ports.outbound.tier_pack_gateway import TierPackContext
from projectg.application.use_cases.tier_packs.get_tier_pack import GetTierPack
from projectg.application.use_cases.tier_packs.requests import SaveTierPackRequest, ValidateTierPackRequest
from projectg.application.use_cases.tier_packs.save_tier_pack import SaveTierPack
from projectg.application.use_cases.tier_packs.validate_tier_pack import ValidateTierPack


class FakeGateway:
    def __init__(self):
        self.committed = None
        self.pack = {
            "version": 1,
            "ratings": {},
            "minimumTierForRoadmap": "B",
            "controls": {},
            "selectedSets": {},
            "packVersion": 2,
        }

    def load_context(self):
        return TierPackContext(
            pack=self.pack,
            pack_hash="hash-2",
            owned_characters=frozenset({"Amber"}),
            character_keys=frozenset({"Amber"}),
            artifact_set_keys=frozenset({"SetA"}),
            set_options={"Amber": ("SetA",)},
        )

    def commit_validated(self, payload):
        self.committed = payload
        self.pack = {**payload, "packVersion": 3}
        return self.pack


def test_tier_pack_query_builds_application_view_from_gateway_facts():
    values = GetTierPack(FakeGateway()).execute().values

    assert values["pack"]["packVersion"] == 2
    assert values["hash"] == "hash-2"
    assert values["rows"] == [{
        "characterKey": "Amber",
        "score": None,
        "notes": "",
        "tier": "Unranked",
        "owned": True,
        "control": "NORMAL",
        "selectedSet": None,
        "setOptions": ["SetA"],
    }]


def test_tier_pack_save_validates_in_application_before_commit():
    gateway = FakeGateway()
    request = SaveTierPackRequest({
        "version": 1,
        "ratings": {"Amber": {"score": 90, "notes": " Top "}},
        "minimumTierForRoadmap": "B",
        "controls": {},
        "selectedSets": {"Amber": "SetA"},
    })

    saved = SaveTierPack(gateway).execute(request)

    assert gateway.committed["ratings"]["Amber"] == {"score": 90, "notes": "Top"}
    assert saved.values["packVersion"] == 3


def test_tier_pack_validation_is_an_application_action():
    gateway = FakeGateway()
    payload = {"version": 1, "ratings": {"Amber": {"score": 80, "notes": ""}}}

    result = ValidateTierPack(gateway).execute(ValidateTierPackRequest(payload))

    assert gateway.committed is None
    assert result.values == {
        "version": 1,
        "ratings": {"Amber": {"score": 80, "notes": ""}},
        "minimumTierForRoadmap": "B",
        "controls": {},
        "selectedSets": {},
    }
