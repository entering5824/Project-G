from projectg.application.ports.outbound.character_configuration_gateway import CharacterConfigurationData
from projectg.interface_adapters.controllers.character_configuration_controller import CharacterConfigurationController


class UseCase:
    def __init__(self, result):
        self.result = result
        self.request = None

    def execute(self, request):
        self.request = request
        return self.result


def test_controller_maps_configuration_response_to_desktop_shape():
    data = CharacterConfigurationData("Amber", 2, (), "T1", 3, "NORMAL", "default", ())
    get = UseCase(data)
    save = UseCase(data)
    controller = CharacterConfigurationController(get, save)

    result = controller.load("Amber")

    assert result["characterKey"] == "Amber"
    assert result["tierAssignmentVersion"] == 3
