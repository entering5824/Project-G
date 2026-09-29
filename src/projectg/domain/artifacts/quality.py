from math import isfinite
from math import ceil

from .models import (ArtifactQualityConfig, ArtifactQualityResult, QUALITY_LABELS,
                     QualityStatus, TARGET_LABEL_SCORE)

METRICS = {"rv": "rv", "cv": "cv", "rank_percent": "rank_percent", "custom_score": "custom_score"}


class ArtifactQualityAdapter:
    """Maps a raw, explicitly selected metric to a stable [0, 1] quality scale."""

    def evaluate(self, evaluation: dict | None, target_quality: str,
                 config: ArtifactQualityConfig, *, current_fingerprint: str | None = None) -> ArtifactQualityResult:
        if not evaluation:
            return ArtifactQualityResult(QualityStatus.UNKNOWN, None, None, None, None)
        raw = evaluation.get("rawMetrics", evaluation)
        slots = raw.get("slots") if isinstance(raw, dict) else None
        weak_slots = self._weak_slots(slots)
        stale = bool(evaluation.get("stale") or
                     (evaluation.get("artifactFingerprint") and
                      evaluation["artifactFingerprint"] != current_fingerprint))

        direct = raw.get("normalized_score") if isinstance(raw, dict) else None
        if raw.get("developerInput") is True and direct is not None:
            if not _valid_number(direct) or not 0 <= float(direct) <= 1:
                return ArtifactQualityResult(QualityStatus.INVALID_DATA, None, None, None, None,
                                             weak_slots, "normalized_score", stale, True,
                                             "Developer normalized input must be between 0 and 1.")
            score = float(direct)
            target = TARGET_LABEL_SCORE.get(target_quality)
            status = QualityStatus.COMPLETE if target is not None and score >= target else QualityStatus.BELOW_TARGET
            deficiency = max(0.0, min(1.0, (target - score) / target)) if target and target > 0 else 0.0
            return ArtifactQualityResult(status, score, "DEVELOPER_INPUT", target, deficiency,
                                         weak_slots, "normalized_score", stale, True)

        metric_key = METRICS.get(config.adapter_type)
        if not metric_key:
            return ArtifactQualityResult(QualityStatus.NEEDS_QUALITY_CONFIG, None, None, None, None,
                                         weak_slots, message="Choose a supported artifact metric adapter.")
        metric = raw.get(metric_key) if isinstance(raw, dict) else None
        if metric is None:
            extras = raw.get("extraMetrics", {}) if isinstance(raw, dict) else {}
            metric = extras.get(metric_key) if isinstance(extras, dict) else None
        if metric is None:
            return ArtifactQualityResult(QualityStatus.INVALID_DATA, None, None, None, None,
                                         weak_slots, metric_key, stale,
                                         message=f"The evaluation has no {metric_key} metric.")
        if not _valid_number(metric) or float(metric) < 0:
            return ArtifactQualityResult(QualityStatus.INVALID_DATA, None, None, None, None,
                                         weak_slots, metric_key, stale,
                                         message=f"The {metric_key} metric must be finite and non-negative.")
        if not config.configured:
            return ArtifactQualityResult(QualityStatus.NEEDS_QUALITY_CONFIG, None, None, None, None,
                                         weak_slots, metric_key, stale,
                                         message="Artifact quality thresholds are not configured.")
        thresholds = [float(config.thresholds[key]) for key in QUALITY_LABELS]
        value = float(metric)
        if config.adapter_type == "rank_percent":
            # Akasha reports a top-percent rank: smaller percentages indicate a
            # stronger leaderboard result. Thresholds therefore descend from
            # POOR to EXCELLENT (for example 100, 50, 10, 1).
            if value >= thresholds[0]:
                score, label = 0.0, "POOR"
            elif value <= thresholds[3]:
                score, label = 1.0, "EXCELLENT"
            else:
                score, label = 0.0, "POOR"
                for index in range(3):
                    poor_boundary, next_boundary = thresholds[index], thresholds[index + 1]
                    if value > next_boundary:
                        score = index / 3 + (poor_boundary - value) / (poor_boundary - next_boundary) / 3
                        label = QUALITY_LABELS[index]
                        break
        elif value < thresholds[0]:
            score, label = 0.0, "POOR"
        else:
            score, label = 0.0, "POOR"
            for index in range(3):
                low, high = thresholds[index], thresholds[index + 1]
                if value < high:
                    score = index / 3 + (value - low) / (high - low) / 3
                    label = QUALITY_LABELS[index]
                    break
            else:
                score, label = 1.0, "EXCELLENT"
            if value >= thresholds[3]:
                score, label = 1.0, "EXCELLENT"
        target = TARGET_LABEL_SCORE.get(target_quality)
        if target is None:
            return ArtifactQualityResult(QualityStatus.INVALID_DATA, score, label, None, None,
                                         weak_slots, metric_key, stale,
                                         message="Unknown target quality label.")
        deficiency = max(0.0, min(1.0, (target - score) / target)) if target else 0.0
        status = QualityStatus.COMPLETE if score >= target else QualityStatus.BELOW_TARGET
        return ArtifactQualityResult(status, round(score, 6), label, target, round(deficiency, 6),
                                     weak_slots, metric_key, stale)

    @staticmethod
    def _weak_slots(slots) -> list[str]:
        if not isinstance(slots, dict):
            return []
        values = [(str(key), float(value)) for key, value in slots.items()
                  if _valid_number(value) and float(value) >= 0]
        if len(values) < 2:
            return []
        values.sort(key=lambda pair: (pair[1], pair[0]))
        count = min(2, max(1, ceil(len(values) / 3)))
        return [key for key, _ in values[:count]]


def _valid_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))
