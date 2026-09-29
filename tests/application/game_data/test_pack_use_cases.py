from projectg.application.game_data.policy import account_coverage, catalog_coverage
from projectg.application.ports.outbound.game_data_account_gateway import AccountCatalogFacts
from projectg.application.ports.outbound.game_data_pack_storage import (
    GameDataInstallReceipt,
    GameDataPackDocument,
)
from projectg.application.use_cases.game_data.export_pack import ExportGameDataPack
from projectg.application.use_cases.game_data.get_installed_status import GetInstalledGameDataStatus
from projectg.application.use_cases.game_data.install_pack import InstallGameDataPack
from projectg.application.use_cases.game_data.preview_pack import PreviewGameDataPack
from projectg.application.use_cases.game_data.requests import GameDataPathRequest
from projectg.domain.game_catalog.models import CharacterDefinition, GameData, WeaponDefinition


def _data(version: str, *, characters=(), weapons=()) -> GameData:
    return GameData(
        metadata={
            "schema_version": "1",
            "game_version": "6.0",
            "data_version": version,
            "generated_at": "2026-09-26T00:00:00Z",
            "source": "test",
        },
        characters={
            key: CharacterDefinition(
                key=key,
                rarity=5,
                element="Pyro",
                weapon_type="Sword",
                region="Mondstadt",
                local_specialty="local",
                normal_boss_material=None,
                enemy_material_family="enemy",
                talent_book_family="talent",
                weekly_boss_materials=(),
            )
            for key in characters
        },
        weapons={
            key: WeaponDefinition(
                key=key,
                name=key,
                rarity=5,
                weapon_type="Sword",
                weapon_ascension_material_family=None,
                enemy_material_family=None,
            )
            for key in weapons
        },
    )


class FakeStorage:
    def __init__(self):
        self.installed = GameDataPackDocument("installed.json", _data("current", characters=("Amber",)))
        self.candidate = GameDataPackDocument(
            "candidate.json", _data("candidate", characters=("Amber", "Furina"), weapons=("Sword",))
        )
        self.calls = []

    def load_installed(self):
        self.calls.append(("load_installed", None))
        return self.installed

    def load_candidate(self, path):
        self.calls.append(("load_candidate", path))
        return self.candidate

    def install_candidate(self, path):
        self.calls.append(("install_candidate", path))
        self.installed = GameDataPackDocument("installed.json", self.candidate.data)
        return GameDataInstallReceipt("installed.json", "backup.json")

    def export_installed(self, destination):
        self.calls.append(("export_installed", destination))
        return destination


class FakeAccountGateway:
    def __init__(self):
        self.calls = 0

    def load_catalog_facts(self):
        self.calls += 1
        return AccountCatalogFacts(
            character_keys=("Amber", "FutureCharacter"),
            equipped_weapon_keys=("Sword", "FutureWeapon"),
        )


def test_status_use_case_projects_installed_pack_and_account_coverage():
    storage = FakeStorage()
    account = FakeAccountGateway()

    result = GetInstalledGameDataStatus(storage, account).execute()

    assert result.path == "installed.json"
    assert result.metadata["dataVersion"] == "current"
    assert result.account_coverage["missingCharacters"] == ["FutureCharacter"]
    assert result.account_coverage["missingWeapons"] == ["FutureWeapon", "Sword"]
    assert storage.calls == [("load_installed", None)]
    assert account.calls == 1


def test_preview_is_application_composition_not_storage_proxy():
    storage = FakeStorage()
    account = FakeAccountGateway()

    result = PreviewGameDataPack(storage, account).execute(GameDataPathRequest("candidate.json"))

    assert result.metadata["dataVersion"] == "candidate"
    assert result.current is not None
    assert result.current.metadata["dataVersion"] == "current"
    assert result.account_coverage["knownCharacters"] == 1
    assert result.account_coverage["knownWeapons"] == 1
    assert storage.calls == [
        ("load_candidate", "candidate.json"),
        ("load_installed", None),
    ]


def test_install_validates_before_mutation_then_projects_installed_pack():
    storage = FakeStorage()
    account = FakeAccountGateway()

    result = InstallGameDataPack(storage, account).execute(GameDataPathRequest("candidate.json"))

    assert result.metadata["dataVersion"] == "candidate"
    assert result.backup_path == "backup.json"
    assert storage.calls == [
        ("load_candidate", "candidate.json"),
        ("install_candidate", "candidate.json"),
        ("load_installed", None),
    ]


def test_export_uses_installed_metadata_but_storage_owns_file_copy():
    storage = FakeStorage()

    result = ExportGameDataPack(storage).execute(GameDataPathRequest("export.json"))

    assert result.path == "export.json"
    assert result.metadata["dataVersion"] == "current"
    assert result.coverage == {}
    assert storage.calls == [
        ("load_installed", None),
        ("export_installed", "export.json"),
    ]


def test_catalog_and_account_coverage_are_pure_application_policy():
    data = _data("v", characters=("Amber",), weapons=("Sword",))
    facts = AccountCatalogFacts(("Amber", "Missing"), ("Sword", "Unknown"))

    assert catalog_coverage(data)["characters"] == 1
    coverage = account_coverage(data, facts)
    assert coverage["knownCharacters"] == 1
    assert coverage["missingCharacters"] == ["Missing"]
    assert coverage["knownWeapons"] == 1
    assert coverage["missingWeapons"] == ["Unknown"]
