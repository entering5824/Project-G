from projectg.application.ports.outbound.teams_gateway import TeamsData
from projectg.interface_adapters.controllers.teams_controller import TeamsController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request=None):
        self.request = request
        return self.result


def test_teams_controller_maps_application_data_to_desktop_payload():
    get_teams = UseCase(TeamsData(("Amber",), ({"teamId": "imported"},), ()))
    save_teams = UseCase(TeamsData(("Amber",), (), ({"teamId": "new"},)))
    controller = TeamsController(get_teams, save_teams)

    loaded = controller.load()
    saved = controller.save([{"teamId": "new"}])

    assert loaded == {"ownedCharacters": ["Amber"],
                      "importedTeams": [{"teamId": "imported"}], "configuredTeams": []}
    assert saved["configuredTeams"] == [{"teamId": "new"}]
    assert save_teams.request.rows == ({"teamId": "new"},)
