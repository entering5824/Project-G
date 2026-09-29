from projectg.application.ports.outbound.file_storage import FileStorage
from projectg.application.ports.outbound.tier_pack_gateway import TierPackData
from projectg.interface_adapters.controllers.tier_pack_controller import TierPackController


class UseCase:
    def __init__(self, value):
        self.value = value
        self.request = None

    def execute(self, request=None):
        self.request = request
        return TierPackData(self.value)


class MemoryStorage(FileStorage):
    def __init__(self, content=b'{"version": 1, "ratings": {}}'):
        self.content = content
        self.writes = []

    def read(self, key):
        assert key == "tier.json"
        return self.content

    def write(self, key, content):
        self.writes.append((key, content))

    def delete(self, key):
        raise AssertionError("not used")


def test_tier_pack_controller_routes_json_file_through_validation_and_storage():
    storage = MemoryStorage()
    get_pack = UseCase({"rows": []})
    save_pack = UseCase({"packVersion": 3})
    validate = UseCase({"version": 1, "ratings": {}})
    controller = TierPackController(get_pack, save_pack, validate, storage)

    imported = controller.import_file("tier.json")
    controller.export_file("tier.json", {"version": 1, "ratings": {}})

    assert imported == {"packVersion": 3}
    assert validate.request.payload == {"version": 1, "ratings": {}}
    assert storage.writes[0][0] == "tier.json"
    assert b'"version": 1' in storage.writes[0][1]
