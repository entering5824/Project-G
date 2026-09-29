import pytest

from projectg.application.ports.outbound.teams_gateway import TeamsData
from projectg.application.use_cases.teams.get_teams import GetTeams
from projectg.application.use_cases.teams.save_teams import SaveTeams, SaveTeamsRequest


class FakeTeamsGateway:
    def __init__(self):
        self.committed = None
        self.data = TeamsData(("Amber",), (), ({"teamId": "a", "name": "A", "members": ["Amber"], "isPrimary": False},))

    def load(self):
        return self.data

    def commit_validated(self, rows):
        self.committed = rows
        return TeamsData(("Amber",), (), tuple(rows))


def test_get_teams_returns_gateway_data():
    teams = GetTeams(FakeTeamsGateway()).execute()

    assert teams.owned_characters == ("Amber",)
    assert teams.configured_teams[0]["teamId"] == "a"


def test_save_teams_normalizes_rows_before_commit():
    gateway = FakeTeamsGateway()
    request = SaveTeamsRequest(({"name": "Primary Team", "members": ["Amber"]},))

    result = SaveTeams(gateway).execute(request)

    assert gateway.committed == [{
        "teamId": "primary-team",
        "name": "Primary Team",
        "members": ["Amber"],
        "isPrimary": False,
    }]
    assert result.configured_teams == tuple(gateway.committed)


def test_save_teams_rejects_unowned_members_before_commit():
    gateway = FakeTeamsGateway()

    with pytest.raises(ValueError, match="unowned"):
        SaveTeams(gateway).execute(
            SaveTeamsRequest(({"name": "Bad", "members": ["Unknown"]},))
        )

    assert gateway.committed is None
