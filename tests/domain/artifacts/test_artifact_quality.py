from projectg.domain.artifacts.models import ArtifactQualityConfig, QualityStatus
from projectg.domain.artifacts.quality import ArtifactQualityAdapter
from projectg.domain.artifacts.validation import validate_metrics, validate_quality_config


def quality_config():
    return ArtifactQualityConfig(version=4, adapter_type="rv",
        thresholds={"POOR":100,"ACCEPTABLE":200,"GOOD":300,"EXCELLENT":400})


def test_missing_evaluation_is_unknown_and_not_a_bad_build():
    result=ArtifactQualityAdapter().evaluate(None,"GOOD",quality_config())
    assert result.status==QualityStatus.UNKNOWN
    assert result.normalized_score is None and result.deficiency is None


def test_raw_metric_maps_through_configured_thresholds_and_target():
    adapter=ArtifactQualityAdapter()
    below=adapter.evaluate({"rawMetrics":{"rv":250}},"GOOD",quality_config())
    assert below.status==QualityStatus.BELOW_TARGET
    assert 0.49 < below.normalized_score < 0.51
    assert below.deficiency==0.25
    complete=adapter.evaluate({"rawMetrics":{"rv":350}},"GOOD",quality_config())
    assert complete.status==QualityStatus.COMPLETE
    assert complete.quality_label=="GOOD"
    assert complete.normalized_score > complete.target_score


def test_missing_threshold_and_missing_primary_metric_are_explicit():
    adapter=ArtifactQualityAdapter()
    assert adapter.evaluate({"rawMetrics":{"rv":500}},"GOOD",ArtifactQualityConfig()).status==QualityStatus.NEEDS_QUALITY_CONFIG
    assert adapter.evaluate({"rawMetrics":{"cv":50}},"GOOD",quality_config()).status==QualityStatus.INVALID_DATA


def test_developer_score_is_explicit_and_weak_slots_are_diagnostic():
    result=ArtifactQualityAdapter().evaluate({"rawMetrics":{"developerInput":True,"normalized_score":0.5,
        "slots":{"flower":500,"plume":480,"sands":300,"goblet":220,"circlet":550}}},"GOOD",ArtifactQualityConfig())
    assert result.status==QualityStatus.BELOW_TARGET and result.developer_input
    assert result.weak_slots==["goblet","sands"]


def test_stale_fingerprint_is_reported_without_invalidating_confirmed_evaluation():
    result=ArtifactQualityAdapter().evaluate({"rawMetrics":{"rv":350},"artifactFingerprint":"old"},
        "GOOD",quality_config(),current_fingerprint="new")
    assert result.status==QualityStatus.COMPLETE and result.stale


def test_metric_and_threshold_validation():
    assert validate_metrics({"rv":123,"slots":{"goblet":20}})["rv"]==123
    try:
        validate_quality_config({"adapterType":"rv","thresholds":{"POOR":5,"ACCEPTABLE":4,"GOOD":8,"EXCELLENT":9}})
        assert False, "non-monotonic thresholds must be rejected"
    except ValueError as exc:
        assert "increase strictly" in str(exc)
    try:
        validate_metrics({"normalized_score":0.7})
        assert False, "direct scores require explicit developer mode"
    except ValueError as exc:
        assert "developer_input=true" in str(exc)
