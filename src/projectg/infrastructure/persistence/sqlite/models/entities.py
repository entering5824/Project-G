from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean, Float, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from projectg.infrastructure.persistence.sqlite.base import Base

def now(): return datetime.now(timezone.utc)

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    server_region: Mapped[str] = mapped_column(String, nullable=False)
    game_language: Mapped[str] = mapped_column(String, nullable=False, default="en", server_default="en")
    world_level: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default="8")
    resin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_claimed_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    unavailable_sources_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    current_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    good_format: Mapped[str] = mapped_column(String)
    good_version: Mapped[int | None] = mapped_column(Integer)
    good_db_version: Mapped[int | None] = mapped_column(Integer)
    raw_file_hash: Mapped[str] = mapped_column(String)
    canonical_state_hash: Mapped[str] = mapped_column(String)
    previous_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("snapshots.id"))
    importer_version: Mapped[str] = mapped_column(String)
    raw_path: Mapped[str] = mapped_column(String)
    coverage_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    effective_state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

class SnapshotCharacter(Base):
    __tablename__ = "snapshot_characters"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String, primary_key=True)
    level: Mapped[int] = mapped_column(Integer)
    ascension: Mapped[int] = mapped_column(Integer)
    constellation: Mapped[int] = mapped_column(Integer)
    talent_auto: Mapped[int] = mapped_column(Integer)
    talent_skill: Mapped[int] = mapped_column(Integer)
    talent_burst: Mapped[int] = mapped_column(Integer)
    equipped_weapon_instance_id: Mapped[str | None] = mapped_column(String)

class SnapshotWeapon(Base):
    __tablename__ = "snapshot_weapons"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    weapon_instance_id: Mapped[str] = mapped_column(String, primary_key=True)
    weapon_key: Mapped[str] = mapped_column(String)
    level: Mapped[int] = mapped_column(Integer)
    ascension: Mapped[int] = mapped_column(Integer)
    refinement: Mapped[int] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String)

class SnapshotArtifact(Base):
    __tablename__ = "snapshot_artifacts"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    artifact_instance_id: Mapped[str] = mapped_column(String, primary_key=True)
    character_key: Mapped[str] = mapped_column(String, index=True)
    set_key: Mapped[str] = mapped_column(String)
    slot_key: Mapped[str] = mapped_column(String)
    rarity: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer)
    main_stat_key: Mapped[str] = mapped_column(String)
    substats_json: Mapped[list] = mapped_column(JSON)
    unactivated_substats_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rv: Mapped[float | None] = mapped_column(Float, nullable=True)
    rv_status: Mapped[str] = mapped_column(String, nullable=False, default="UNKNOWN")
    rv_formula_version: Mapped[str] = mapped_column(String, nullable=False, default="artifact-rv-1")

class SnapshotTeam(Base):
    __tablename__ = "snapshot_teams"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)
    members_json: Mapped[list] = mapped_column(JSON)
    raw_config_json: Mapped[dict | None] = mapped_column(JSON)

class CharacterTargetVersion(Base):
    __tablename__ = "character_target_versions"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String, primary_key=True)
    preset_key: Mapped[str] = mapped_column(String, nullable=False, default="default", server_default="default")
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class CharacterTargetPreset(Base):
    __tablename__ = "character_target_presets"
    __table_args__ = (Index("uq_target_preset_active", "account_id", "character_key",
        unique=True, sqlite_where=text("is_active = 1")),)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String, primary_key=True)
    preset_key: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TierConfigVersion(Base):
    __tablename__ = "tier_config_versions"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    tiers_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TierPackVersion(Base):
    __tablename__ = "tier_pack_versions"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    pack_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TierAssignmentVersion(Base):
    __tablename__ = "tier_assignment_versions"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier_key: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class CharacterPriority(Base):
    __tablename__ = "character_priorities"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String, primary_key=True)
    override: Mapped[str] = mapped_column(String, nullable=False, default="NORMAL")
class AccountPlanningIntent(Base):
    __tablename__ = "account_planning_intents"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    personal_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    theater_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

class PlannerConfigVersion(Base):
    __tablename__ = "planner_config_versions"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PlannerFeedback(Base):
    __tablename__ = "planner_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    planner_context_hash: Mapped[str] = mapped_column(String, index=True)
    goal_key: Mapped[str] = mapped_column(String, index=True)
    character_key: Mapped[str] = mapped_column(String)
    goal_type: Mapped[str] = mapped_column(String)
    tier_key: Mapped[str | None] = mapped_column(String)
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    rating: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    current_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    target_json: Mapped[dict] = mapped_column(JSON, nullable=False)

class ArtifactEvaluation(Base):
    __tablename__ = "artifact_evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    character_key: Mapped[str] = mapped_column(String, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source: Mapped[str] = mapped_column(String, nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String, nullable=False, default="CONFIRMED")
    raw_metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    parser_confidence: Mapped[float | None] = mapped_column(Float)
    artifact_fingerprint: Mapped[str | None] = mapped_column(String)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("artifact_evaluations.id"))

class ArtifactQualityConfigVersion(Base):
    __tablename__ = "artifact_quality_config_versions"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    character_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)

class IdempotencyReceipt(Base):
    __tablename__ = "idempotency_receipts"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class TodayState(Base):
    __tablename__ = "today_state"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    pursued_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pursued_character_key: Mapped[str | None] = mapped_column(String, nullable=True)
    pursued_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ordering_group: Mapped[str | None] = mapped_column(String, nullable=True)
    pursued_config_version: Mapped[str | None] = mapped_column(String, nullable=True)
    pinned_character_key: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PlanRun(Base):
    __tablename__ = "plan_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="TODAY")
    snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True)
    normalized_input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    target_versions_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    planner_config_version: Mapped[str] = mapped_column(String, nullable=False)
    source_availability_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    hysteresis_state_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
    game_data_version: Mapped[str | None] = mapped_column(String, nullable=True)
    rv_formula_version: Mapped[str] = mapped_column(String, nullable=False)
    switch_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class PlannerTeam(Base):
    __tablename__ = "planner_teams"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    members_json: Mapped[list] = mapped_column(JSON, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
