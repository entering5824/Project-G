from projectg.domain.account.models import (
    ArtifactState,
    CharacterState,
    NormalizedGood,
    TeamState,
    WeaponState,
)
from projectg.domain.history.diff import compare_account_snapshots


def _snapshot(*, level: int, weapon_level: int, artifact_level: int, team_members):
    return NormalizedGood(
        "GOOD",
        1,
        1,
        [CharacterState("amber", level, 5, 1, 6, 8, 8, "w1")],
        [WeaponState("w1", "FavoniusBow", weapon_level, 5, 2, "amber")],
        [
            ArtifactState(
                "a1",
                "amber",
                "set-a",
                "flower",
                5,
                artifact_level,
                "hp",
            )
        ],
        [TeamState("t1", "Main", list(team_members))],
    )


def test_snapshot_diff_policy_is_independent_of_sqlite_models():
    before = _snapshot(level=70, weapon_level=70, artifact_level=16, team_members=["amber"])
    after = _snapshot(level=80, weapon_level=80, artifact_level=20, team_members=["amber", "lisa"])

    diff = compare_account_snapshots(
        before,
        after,
        from_snapshot_id="before",
        to_snapshot_id="after",
    )

    event_types = [item["eventType"] for item in diff["changes"]]
    assert "CHARACTER_LEVEL_CHANGED" in event_types
    assert "WEAPON_LEVEL_CHANGED" in event_types
    assert "ARTIFACT_PIECE_CHANGED" in event_types
    assert "TEAM_CHANGED" in event_types
    assert diff["summary"]["totalChanges"] == len(diff["changes"])
