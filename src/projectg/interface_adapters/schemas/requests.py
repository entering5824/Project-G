"""Strict validation contracts for native mutation payloads."""
from __future__ import annotations

from math import isfinite
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, RootModel, StrictBool, StrictInt, StrictStr, model_validator


def _numeric(value: object) -> float:
    # JSON numbers may arrive as integers or floats; reject bools and strings,
    # and keep conversion failures (including huge integers) within Pydantic's 422 path.
    if type(value) not in (int, float):
        raise ValueError("value must be a finite JSON number")
    try:
        normalized = float(value)
    except (OverflowError, ValueError):
        raise ValueError("value must be a finite JSON number") from None
    if not isfinite(normalized):
        raise ValueError("value must be a finite JSON number")
    return normalized


def _key(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string")
    return value.strip()


FiniteNumber = Annotated[float, BeforeValidator(_numeric)]
NonNegativeNumber = Annotated[FiniteNumber, Field(ge=0)]
Key = Annotated[StrictStr, BeforeValidator(_key)]
ArtifactSetKey = Annotated[StrictStr, BeforeValidator(_key), Field(max_length=128)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ArtifactPreviewRequest(RootModel[dict[str, object] | list[object]]):
    """Typed top-level JSON shape; semantic row errors stay in the preview response."""
    model_config = ConfigDict(strict=True)


class PlannerWeights(StrictModel):
    deficiency: FiniteNumber
    importance: FiniteNumber
    tier: FiniteNumber
    team: FiniteNumber
    completion: FiniteNumber


class PriorityMultipliers(StrictModel):
    normal: FiniteNumber
    prioritized: FiniteNumber
    deprioritized: FiniteNumber


class PlannerConfigRequest(StrictModel):
    weights: PlannerWeights | None = None
    tier_fallback: FiniteNumber | None = Field(default=None, alias="tierFallback")
    team_primary: FiniteNumber | None = Field(default=None, alias="teamPrimary")
    team_saved: FiniteNumber | None = Field(default=None, alias="teamSaved")
    team_none: FiniteNumber | None = Field(default=None, alias="teamNone")
    priority_override: PriorityMultipliers | None = Field(default=None, alias="priorityOverride")
    completion_near_threshold: FiniteNumber | None = Field(default=None, alias="completionNearThreshold")
    horizon: StrictInt | None = None
    reorder_threshold: FiniteNumber | None = Field(default=None, alias="reorderThreshold")
    manual_order_enabled: StrictBool | None = Field(default=None, alias="manualOrderEnabled")
    manual_order: list[Key] | None = Field(default=None, alias="manualOrder")


class PlannerConfigWrite(StrictModel):
    config: PlannerConfigRequest | None = None
    reset_to_baseline: StrictBool = Field(default=False, alias="resetToBaseline")

    @model_validator(mode="after")
    def require_config_or_reset(self):
        if not self.reset_to_baseline and self.config is None:
            raise ValueError("config is required unless resetToBaseline is true")
        if self.reset_to_baseline and self.config is not None:
            raise ValueError("config cannot be sent with resetToBaseline")
        return self


class PlannerPreviewWrite(StrictModel):
    config: PlannerConfigRequest


class PlannerFeedbackWrite(StrictModel):
    goal_key: Key = Field(alias="goalKey")
    rating: Literal["OK", "TOO_HIGH", "TOO_LOW", "WRONG"]
    note: Annotated[StrictStr, Field(max_length=2000)] | None = None


class ArtifactGate(StrictModel):
    min_level: StrictInt | None = Field(default=None, alias="minLevel")
    min_ascension: StrictInt | None = Field(default=None, alias="minAscension")
    weapon_min_level: StrictInt | None = Field(default=None, alias="weaponMinLevel")
    required_talents: list[Literal["normal", "skill", "burst"]] = Field(default_factory=list, alias="requiredTalents")


class TalentTargetRequest(StrictModel):
    enabled: StrictBool
    target: StrictInt
    importance: FiniteNumber


class TalentTargetsRequest(StrictModel):
    normal: TalentTargetRequest
    skill: TalentTargetRequest
    burst: TalentTargetRequest


class TargetImportance(StrictModel):
    level: FiniteNumber
    ascension: FiniteNumber


class WeaponTargetRequest(StrictModel):
    weapon_key: Key | None = Field(default=None, alias="weaponKey")
    target_level: StrictInt = Field(alias="targetLevel")
    importance: FiniteNumber


class ArtifactTargetRequest(StrictModel):
    enabled: StrictBool
    target_quality: Literal["ACCEPTABLE", "GOOD", "EXCELLENT"] = Field(alias="targetQuality")
    importance: FiniteNumber
    primary_sets: Annotated[list[ArtifactSetKey], Field(max_length=20)] = Field(alias="primarySets")
    alternative_sets: Annotated[list[ArtifactSetKey], Field(max_length=20)] = Field(alias="alternativeSets")
    gate: ArtifactGate = Field(default_factory=ArtifactGate)

    @model_validator(mode="after")
    def require_unique_set_keys(self):
        all_keys = [*self.primary_sets, *self.alternative_sets]
        if len(all_keys) != len(set(all_keys)):
            raise ValueError("Artifact set keys must be unique across primary and alternative sets")
        return self


class CharacterTargetRequest(StrictModel):
    level: StrictInt
    ascension: StrictInt
    importance: TargetImportance
    talents: TalentTargetsRequest
    weapon: WeaponTargetRequest
    artifact: ArtifactTargetRequest
    notes: Annotated[StrictStr, Field(max_length=2000)]


class TargetImportRequest(StrictModel):
    version: Literal[1]
    # Validate each imported row independently in the import preview so one
    # malformed character target does not discard otherwise valid targets.
    targets: dict[Key, Any]


class TargetPresetCreate(StrictModel):
    label: Annotated[StrictStr, Field(min_length=1, max_length=80)]


class TargetWriteRequest(CharacterTargetRequest):
    pass


class BulkTargetEntry(StrictModel):
    character_key: Key = Field(alias="characterKey")
    target: CharacterTargetRequest


class BulkTargetsWrite(StrictModel):
    targets: Annotated[list[BulkTargetEntry], Field(min_length=1)]


class TierRequest(StrictModel):
    key: Key
    label: Key
    weight: NonNegativeNumber
    order: StrictInt


class TiersWrite(StrictModel):
    tiers: Annotated[list[TierRequest], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_keys(self):
        keys = [tier.key for tier in self.tiers]
        if len(keys) != len(set(keys)):
            raise ValueError("Tier keys must be unique")
        return self


class TierAssignmentWrite(StrictModel):
    tier_key: StrictStr | None = Field(default=None, alias="tierKey")


class BulkTierAssignmentRequest(StrictModel):
    character_key: Key = Field(alias="characterKey")
    tier_key: StrictStr | None = Field(default=None, alias="tierKey")


class BulkTierAssignmentsRequest(StrictModel):
    assignments: Annotated[list[BulkTierAssignmentRequest], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_characters(self):
        keys = [assignment.character_key for assignment in self.assignments]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate character keys are not allowed")
        return self


class ArtifactQualityThresholds(StrictModel):
    POOR: NonNegativeNumber | None
    ACCEPTABLE: NonNegativeNumber | None
    GOOD: NonNegativeNumber | None
    EXCELLENT: NonNegativeNumber | None


class ArtifactQualityWrite(StrictModel):
    adapter_type: Literal["rv", "cv", "custom_score"] = Field(alias="adapterType")
    thresholds: ArtifactQualityThresholds


class ArtifactSlotsWrite(StrictModel):
    flower: NonNegativeNumber | None = None
    plume: NonNegativeNumber | None = None
    sands: NonNegativeNumber | None = None
    goblet: NonNegativeNumber | None = None
    circlet: NonNegativeNumber | None = None


class ManualArtifactMetricsWrite(StrictModel):
    rv: NonNegativeNumber | None = None
    cv: NonNegativeNumber | None = None
    rank_percent: NonNegativeNumber | None = None
    custom_score: NonNegativeNumber | None = None
    extra_metrics: dict[Key, FiniteNumber] = Field(default_factory=dict)
    slots: ArtifactSlotsWrite = Field(default_factory=ArtifactSlotsWrite)
    developer_input: StrictBool | None = None
    normalized_score: NonNegativeNumber | None = None


class ManualArtifactWrite(StrictModel):
    character_key: Key = Field(alias="characterKey")
    metrics: ManualArtifactMetricsWrite


class AefMetricsWrite(StrictModel):
    rv: NonNegativeNumber | None = None
    cv: NonNegativeNumber | None = None
    rank_percent: NonNegativeNumber | None = Field(default=None, alias="rankPercent")
    custom_score: NonNegativeNumber | None = Field(default=None, alias="customScore")
    slots: ArtifactSlotsWrite = Field(default_factory=ArtifactSlotsWrite)
    extra: dict[Key, FiniteNumber] = Field(default_factory=dict)


class ArtifactEvaluationWrite(StrictModel):
    character_key: Key = Field(alias="characterKey")
    metrics: AefMetricsWrite
    manually_corrected: StrictBool = Field(default=False, alias="manuallyCorrected")


class ArtifactEvaluationsWrite(StrictModel):
    evaluations: Annotated[list[ArtifactEvaluationWrite], Field(min_length=1)]
    preview_snapshot_id: StrictStr | None = Field(default=None, alias="previewSnapshotId")


class CharacterPriorityWrite(StrictModel):
    override: Literal["NORMAL", "PRIORITIZED", "DEPRIORITIZED"]
