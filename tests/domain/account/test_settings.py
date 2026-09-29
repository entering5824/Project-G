import pytest

from projectg.domain.account.settings import normalize_account_settings


def test_account_settings_normalize_region_lists_and_language():
    result = normalize_account_settings({
        "serverRegion": "europe",
        "gameLanguage": " vi ",
        "worldLevel": 7,
        "resin": None,
        "weeklyClaimed": ["Wolf", "Wolf", ""],
        "unavailableSources": [" DomainA ", "DomainB"],
    })

    assert result == {
        "serverRegion": "EUROPE",
        "gameLanguage": "vi",
        "worldLevel": 7,
        "resin": None,
        "weeklyClaimed": ["Wolf"],
        "unavailableSources": ["DomainA", "DomainB"],
    }


def test_account_settings_reject_invalid_world_level():
    with pytest.raises(ValueError, match="World Level"):
        normalize_account_settings({
            "serverRegion": "ASIA",
            "gameLanguage": "en",
            "worldLevel": 10,
            "resin": 0,
        })
