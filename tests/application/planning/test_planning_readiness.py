from types import SimpleNamespace

from projectg.application.planning.readiness import assess_build_readiness


def _targets():
    return {
        "level": 80,
        "weapon": {"targetLevel": 80},
        "talents": {"normal": {"enabled": False},
                    "skill": {"enabled": True, "target": 8},
                    "burst": {"enabled": True, "target": 8}},
        "_profiles": [{"setCombinations": [{"combination": [{"setKey": "SetA", "pieces": 4}], "utility": 1}]}],
        "_buildArtifacts": [{"slotRvTargets": {
            slot: {"stopFarming": 20} for slot in ("flower", "plume", "sands", "goblet", "circlet")
        }}],
    }


def _character(artifacts):
    return SimpleNamespace(level=80, ascension=6, weapon=SimpleNamespace(level=80),
                           talents={"auto": 1, "skill": 8, "burst": 8}, artifacts=artifacts)


def test_readiness_requires_known_rv_for_equipped_artifacts():
    artifacts = {slot: {"rv": 20, "setKey": "SetA"} for slot in ("flower", "plume", "sands", "goblet", "circlet")}
    artifacts["flower"]["rv"] = None
    result = assess_build_readiness(_character(artifacts), _targets())
    assert result["status"] == "NEEDS_RV"
    assert "Cần điền RV: flower" in result["missing"]


def test_zero_rv_is_known_and_missing_artifact_is_not_requested_for_rv():
    artifacts = {slot: {"rv": 20, "setKey": "SetA"} for slot in ("flower", "plume", "sands", "goblet", "circlet")}
    artifacts["flower"]["rv"] = 0
    result = assess_build_readiness(_character(artifacts), _targets())
    assert result["status"] == "IN_PROGRESS"
    assert "Cần điền RV: flower" not in result["missing"]
    artifacts.pop("circlet")
    result = assess_build_readiness(_character(artifacts), _targets())
    assert result["status"] == "IN_PROGRESS"
    assert "Chưa có thánh di vật: circlet" in result["missing"]


def test_missing_build_profile_is_never_ready():
    result = assess_build_readiness(_character({}), None)
    assert result == {"status": "UNKNOWN", "missing": ["Thiếu Build Knowledge đã xác minh"]}


def test_readiness_uses_strictest_verified_rv_target():
    targets = _targets()
    targets["_buildArtifacts"].append({"slotRvTargets": {
        slot: {"stopFarming": 30} for slot in ("flower", "plume", "sands", "goblet", "circlet")
    }})
    targets["_profiles"].append(targets["_profiles"][0])
    artifacts = {slot: {"rv": 20, "setKey": "SetA"} for slot in ("flower", "plume", "sands", "goblet", "circlet")}
    result = assess_build_readiness(_character(artifacts), targets)
    assert result["status"] == "IN_PROGRESS"


def test_readiness_can_use_account_good_rv_threshold_when_profile_has_no_slot_cutoffs():
    targets = _targets()
    targets["_buildArtifacts"] = [{}]
    artifacts = {slot: {"rv": 20, "setKey": "SetA"} for slot in ("flower", "plume", "sands", "goblet", "circlet")}
    assert assess_build_readiness(_character(artifacts), targets)["status"] == "UNKNOWN"
    assert assess_build_readiness(_character(artifacts), targets, rv_threshold=18)["status"] == "READY"
