import copy
import json
from zipfile import ZipFile

import pytest

from projectg.presentation.desktop.result_export import export_results


def test_export_preserves_all_result_data_and_explains_primary_task(tmp_path):
    task = {"id": "goal:weapon", "title": "Furina | Weapon 80 → 90", "score": 12.5,
            "actionText": "Farm Mora", "whySummary": "Cần nâng cấp\nnhân vật",
            "availability": "AVAILABLE", "requiredCost": {"Mora": 12000}}
    data = {"snapshotId": 7, "today": {"primaryTask": task, "farming": [task],
            "coverage": {"buildKnowledgeReady": True}},
            "characters": [{"key": "Furina", "tierScore": 90}],
            "roadmap": {"global": [{"rank": 1, "character": {"key": "Furina"},
                                       "type": "WEAPON_LEVEL", "milestoneChain": [{"from": 80, "to": 90}]}]}}
    before = copy.deepcopy(data)
    destination = tmp_path / "results.zip"
    export_results(destination, data)
    with ZipFile(destination) as archive:
        assert set(archive.namelist()) == {"report.md", "results.json", "review.md"}
        payload = json.loads(archive.read("results.json"))
        assert payload["result"] == data
        assert payload["schemaVersion"] == 2
        assert payload["exportedAt"]
        report = archive.read("report.md").decode("utf-8")
        assert "Farm Mora" in report and "12000" in report and "Furina" in report
        assert "Furina \\| Weapon 80 → 90" in report
        assert "Cần nâng cấp nhân vật" in report
        assert "Kết quả mong đợi" in archive.read("review.md").decode("utf-8")
    assert data == before


def test_empty_plan_can_be_reviewed_without_inventing_recommendations(tmp_path):
    destination = tmp_path / "empty.zip"
    export_results(destination, {"snapshotId": 1, "today": {"noActionReason": "NO_STRATEGIC_GOAL"}})
    with ZipFile(destination) as archive:
        assert "NO_STRATEGIC_GOAL" in archive.read("report.md").decode("utf-8")


def test_invalid_result_does_not_overwrite_existing_export(tmp_path):
    destination = tmp_path / "existing.zip"
    destination.write_bytes(b"existing review")
    with pytest.raises(TypeError):
        export_results(destination, {"today": object()})
    assert destination.read_bytes() == b"existing review"
    assert list(tmp_path.iterdir()) == [destination]
