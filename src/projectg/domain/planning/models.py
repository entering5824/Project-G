from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GoalType(StrEnum):
    CHARACTER_LEVEL = "CHARACTER_LEVEL"
    CHARACTER_ASCENSION = "CHARACTER_ASCENSION"
    TALENT_AUTO = "TALENT_AUTO"
    TALENT_SKILL = "TALENT_SKILL"
    TALENT_BURST = "TALENT_BURST"
    WEAPON_LEVEL = "WEAPON_LEVEL"
    ARTIFACT_QUALITY = "ARTIFACT_QUALITY"  # Reserved; intentionally not generated.


class GoalStatus(StrEnum):
    ACTIONABLE = "ACTIONABLE"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"


@dataclass
class WeaponState:
    instance_id: str
    key: str
    level: int
    ascension: int


@dataclass
class CharacterState:
    key: str
    level: int
    ascension: int
    talents: dict[str, int]
    weapon: WeaponState | None = None
    artifact_fingerprint: str | None = None
    constellation: int = 0
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class TierValue:
    key: str
    label: str
    weight: float
    order: int = 0


@dataclass
class PlannerInput:
    """Normalized domain values only. SQLAlchemy objects never enter planner code."""

    characters: dict[str, CharacterState]
    character_targets: dict[str, dict[str, Any]]
    tiers: dict[str, TierValue]
    tier_assignments: dict[str, str]
    priority_overrides: dict[str, str]
    saved_team_members: set[str]
    config: Any
    primary_team_members: set[str] = field(default_factory=set)
    artifact_evaluations: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifact_quality_config: Any = None
    artifact_domains: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Compatibility escape hatch for explicit callers. Normal persisted
    # planning keeps this False so unranked characters stay outside Global
    # until a tier is assigned or the user explicitly prioritizes them.
    include_unranked_in_plan: bool = False
    tier_scores: dict[str, int] = field(default_factory=dict)
    planner_controls: dict[str, str] = field(default_factory=dict)
    minimum_tier_score: int = 34
    selected_sets: dict[str, str] = field(default_factory=dict)
    personal_priority_keys: set[str] = field(default_factory=set)
    theater_priority_keys: set[str] = field(default_factory=set)
    theater_readiness: dict[str, dict[str, Any]] = field(default_factory=dict)
    theater_candidate_keys: list[str] = field(default_factory=list)
    theater_required_characters: int = 0


@dataclass
class ScoreBreakdown:
    deficiency: float
    importance: float
    tier: float
    team: float
    completion: float
    base_score: float
    efficiency: float
    efficiency_modifier: float
    confidence: float
    priority_override: float
    final_score: float
    tier_configured: bool
    tier_label: str
    priority_mode: str
    saved_team_member: bool = False
    primary_team_member: bool = False
    completion_explanation: str = ""
    tier_priority_multiplier: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "deficiency": self.deficiency,
            "importance": self.importance,
            "tier": self.tier,
            "team": self.team,
            "completion": self.completion,
            "baseScore": self.base_score,
            "efficiency": self.efficiency,
            "efficiencyModifier": self.efficiency_modifier,
            "confidence": self.confidence,
            "priorityOverride": self.priority_override,
            "priorityMode": self.priority_mode,
            "savedTeamMember": self.saved_team_member,
            "primaryTeamMember": self.primary_team_member,
            "completionExplanation": self.completion_explanation,
            "tierConfigured": self.tier_configured,
            "tierLabel": self.tier_label,
            "finalScore": self.final_score,
            "tierPriorityMultiplier": self.tier_priority_multiplier,
        }


@dataclass
class MilestoneStep:
    current: Any
    target: Any


@dataclass
class UpgradeGoal:
    id: str
    goal_key: str
    character_key: str
    type: GoalType
    current_value: Any
    target_value: Any
    importance: float
    deficiency: float
    tier_value: float
    team_value: float
    completion_value: float
    base_score: float = 0.0
    final_score: float = 0.0
    priority_override: float = 1.0
    dependencies: list[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.ACTIONABLE
    reason_codes: list[str] = field(default_factory=list)
    summary: str = ""
    title: str = ""
    tier_configured: bool = True
    tier_key: str | None = None
    tier_label: str = "Fallback"
    saved_team_member: bool = False
    primary_team_member: bool = False
    priority_mode: str = "NORMAL"
    weapon_instance_id: str | None = None
    weapon_key: str | None = None
    weapon_ascension: int | None = None
    action_target: Any = None
    strategic_target: Any = None
    next_milestone: Any = None
    blocked_by: list[str] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None
    efficiency: float | None = None
    artifact_status: str | None = None
    artifact_quality_label: str | None = None
    artifact_target_quality: str | None = None
    artifact_target_score: float | None = None
    artifact_weak_slots: list[str] = field(default_factory=list)
    artifact_stale: bool = False
    artifact_developer_input: bool = False
    artifact_domain_candidates: list[dict[str, Any]] = field(default_factory=list)
    artifact_domain: dict[str, Any] | None = None
    artifact_recommended_sets: list[str] = field(default_factory=list)
    artifact_candidate_class: str | None = None
    milestone_chain: list[MilestoneStep] = field(default_factory=list)
    planning_group: str = "NORMAL"

    @property
    def component_label(self) -> str:
        return {GoalType.WEAPON_LEVEL: "Weapon", GoalType.CHARACTER_LEVEL: "Level",
                GoalType.CHARACTER_ASCENSION: "Ascension", GoalType.TALENT_AUTO: "Normal Attack",
                GoalType.TALENT_SKILL: "Skill", GoalType.TALENT_BURST: "Burst",
                GoalType.ARTIFACT_QUALITY: "Artifacts"}[self.type]


@dataclass(frozen=True)
class UnresolvedIssue:
    code: str
    character_key: str | None
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "characterKey": self.character_key, "severity": self.severity,
                "message": self.message, "details": self.details}


@dataclass
class PlannerResult:
    generated_at: str
    planner_version: str
    config_version: str
    configured_characters: int
    configured_tiers: int
    total_characters: int
    generated_goals: int
    blocked_goals: int
    actionable_goals: int
    global_plan: list[UpgradeGoal]
    unresolved: list[UnresolvedIssue]
    tier_fallback: float
    artifact_enabled_characters: int = 0
    artifact_evaluated_characters: int = 0
