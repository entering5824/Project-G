from projectg.application.ports.outbound.overview_gateway import (
    OverviewCharacterFact,
    OverviewContext,
)
from projectg.application.use_cases.overview.get_overview import GetOverview


class FakeGateway:
    def load_context(self):
        return OverviewContext(
            snapshot_id="snap-1",
            today={"primaryTask": None},
            roadmap={"globalPlan": []},
            characters=(OverviewCharacterFact(
                key="Amber",
                level=80,
                ascension=5,
                talents={"normal": 6, "skill": 8, "burst": 8},
                weapon=None,
                artifacts=(),
                tier_score=50,
                build_profiles=(),
                knowledge_coverage={"verifiedBasic": 1},
                teams=(),
                priority_override="PRIORITIZED",
            ),),
        )


def test_get_overview_composes_read_model_from_gateway_facts():
    result = GetOverview(FakeGateway()).execute()

    assert result.values["snapshotId"] == "snap-1"
    assert result.values["characters"][0]["key"] == "Amber"
    assert result.values["characters"][0]["tierScore"] == 50
    assert result.values["characters"][0]["priorityOverride"] == "PRIORITIZED"


def test_get_overview_empty_context_keeps_empty_account_contract():
    class EmptyGateway:
        def load_context(self):
            return OverviewContext(snapshot_id=None)

    assert GetOverview(EmptyGateway()).execute().values == {
        "snapshotId": None,
        "today": None,
        "roadmap": None,
        "characters": [],
    }
