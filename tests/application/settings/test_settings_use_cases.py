from projectg.application.ports.outbound.settings_gateway import SettingsData
from projectg.application.use_cases.settings.get_settings import GetSettings
from projectg.application.use_cases.settings.save_settings import SaveSettings, SaveSettingsRequest
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG, config_payload


class FakeSettingsGateway:
    def __init__(self):
        self.committed = None

    def load(self):
        return SettingsData(
            config_payload(DEFAULT_PLANNER_CONFIG),
            3,
            {"adapterType": "rv", "thresholds": {
                "POOR": None, "ACCEPTABLE": None, "GOOD": None, "EXCELLENT": None,
            }},
            False,
            {"serverRegion": "ASIA"},
        )

    def commit_validated(self, planner, artifact, account):
        self.committed = (planner, artifact, account)
        return SettingsData(planner, 4, artifact, True, account or {})


def test_get_settings_returns_the_application_output_model():
    settings = GetSettings(FakeSettingsGateway()).execute()

    assert settings.planner_version == 3
    assert settings.account["serverRegion"] == "ASIA"


def test_save_settings_normalizes_before_calling_persistence_port():
    gateway = FakeSettingsGateway()
    planner = config_payload(DEFAULT_PLANNER_CONFIG)
    planner["horizon"] = 14
    artifact = {
        "adapterType": "rv",
        "thresholds": {"POOR": 100, "ACCEPTABLE": 200, "GOOD": 300, "EXCELLENT": 400},
    }
    account = {
        "serverRegion": "europe",
        "gameLanguage": " vi ",
        "worldLevel": 7,
        "resin": 0,
        "weeklyClaimed": ["Stormterror", "Stormterror", ""],
        "unavailableSources": [" FreedomDomain "],
    }

    result = SaveSettings(gateway).execute(SaveSettingsRequest(planner, artifact, account))

    committed_planner, committed_artifact, committed_account = gateway.committed
    assert committed_planner["horizon"] == 14
    assert committed_artifact["thresholds"]["GOOD"] == 300.0
    assert committed_account == {
        "serverRegion": "EUROPE",
        "gameLanguage": "vi",
        "worldLevel": 7,
        "resin": 0,
        "weeklyClaimed": ["Stormterror"],
        "unavailableSources": ["FreedomDomain"],
    }
    assert result.planner_version == 4
