import pytest

from projectg.application.artifacts.errors import ArtifactDocumentError
from projectg.infrastructure.serialization.aef_exchange import AefArtifactDocumentParser


def test_aef_parser_normalizes_external_metric_names_without_persistence():
    parsed = AefArtifactDocumentParser().parse({
        "format": "AEF",
        "version": 1,
        "characterKey": "Amber",
        "metrics": {"rv": 250, "extra": {"rollValue": 42}},
    })

    row = parsed[0]
    assert row.character_key == "Amber"
    assert row.metrics["rv"] == 250.0
    assert row.metrics["extraMetrics"] == {"rollValue": 42.0}
    assert row.errors == ()


def test_aef_parser_marks_duplicate_character_rows_without_database_access():
    parsed = AefArtifactDocumentParser().parse({
        "format": "AEF",
        "version": 1,
        "evaluations": [
            {"format": "AEF", "version": 1, "characterKey": "Amber", "metrics": {"rv": 250}},
            {"format": "AEF", "version": 1, "characterKey": "Amber", "metrics": {"rv": 260}},
        ],
    })

    assert len(parsed) == 2
    assert all(row.errors[0]["code"] == "DUPLICATE_CHARACTER_EVALUATION" for row in parsed)


def test_aef_parser_raises_application_boundary_error_for_invalid_root():
    with pytest.raises(ArtifactDocumentError) as exc:
        AefArtifactDocumentParser().parse({"format": "WRONG", "version": 1, "evaluations": [{}]})

    assert exc.value.code == "INVALID_AEF_FORMAT"
