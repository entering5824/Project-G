import pytest

from projectg.domain.teams.configuration import normalize_configured_teams


def test_team_normalization_generates_stable_unique_ids_and_trims_members():
    rows = normalize_configured_teams([
        {"name": "Abyss Team", "members": [" Amber "]},
        {"name": "Abyss Team", "members": ["Amber"]},
    ], owned_characters={"Amber"})

    assert [row["teamId"] for row in rows] == ["abyss-team", "abyss-team-2"]
    assert rows[0]["members"] == ["Amber"]


def test_team_normalization_rejects_duplicate_primary_teams():
    with pytest.raises(ValueError, match="Only one"):
        normalize_configured_teams([
            {"name": "A", "members": ["Amber"], "isPrimary": True},
            {"name": "B", "members": ["Fischl"], "isPrimary": True},
        ], owned_characters={"Amber", "Fischl"})
