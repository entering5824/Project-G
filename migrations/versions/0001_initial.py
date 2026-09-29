"""Initial local account and immutable snapshot schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("accounts",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("name", sa.String(), nullable=False),
        sa.Column("server_region", sa.String(), nullable=False), sa.Column("current_snapshot_id", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("snapshots",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False), sa.Column("good_format", sa.String(), nullable=False),
        sa.Column("good_version", sa.Integer()), sa.Column("good_db_version", sa.Integer()), sa.Column("raw_file_hash", sa.String(), nullable=False),
        sa.Column("canonical_state_hash", sa.String(), nullable=False), sa.Column("previous_snapshot_id", sa.String()),
        sa.Column("importer_version", sa.String(), nullable=False), sa.Column("raw_path", sa.String(), nullable=False))
    op.create_index("ix_snapshots_account_id", "snapshots", ["account_id"])
    op.create_table("snapshot_characters",
        sa.Column("snapshot_id", sa.String(), sa.ForeignKey("snapshots.id"), primary_key=True), sa.Column("character_key", sa.String(), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False), sa.Column("ascension", sa.Integer(), nullable=False), sa.Column("constellation", sa.Integer(), nullable=False),
        sa.Column("talent_auto", sa.Integer(), nullable=False), sa.Column("talent_skill", sa.Integer(), nullable=False), sa.Column("talent_burst", sa.Integer(), nullable=False),
        sa.Column("equipped_weapon_instance_id", sa.String()))
    op.create_table("snapshot_weapons",
        sa.Column("snapshot_id", sa.String(), sa.ForeignKey("snapshots.id"), primary_key=True), sa.Column("weapon_instance_id", sa.String(), primary_key=True),
        sa.Column("weapon_key", sa.String(), nullable=False), sa.Column("level", sa.Integer(), nullable=False), sa.Column("ascension", sa.Integer(), nullable=False),
        sa.Column("refinement", sa.Integer(), nullable=False), sa.Column("location", sa.String()))
    op.create_table("snapshot_artifacts",
        sa.Column("snapshot_id", sa.String(), sa.ForeignKey("snapshots.id"), primary_key=True), sa.Column("artifact_instance_id", sa.String(), primary_key=True),
        sa.Column("character_key", sa.String(), nullable=False), sa.Column("set_key", sa.String(), nullable=False), sa.Column("slot_key", sa.String(), nullable=False),
        sa.Column("rarity", sa.Integer(), nullable=False), sa.Column("level", sa.Integer(), nullable=False), sa.Column("main_stat_key", sa.String(), nullable=False),
        sa.Column("substats_json", sa.JSON(), nullable=False))
    op.create_index("ix_snapshot_artifacts_character_key", "snapshot_artifacts", ["character_key"])
    op.create_table("snapshot_teams",
        sa.Column("snapshot_id", sa.String(), sa.ForeignKey("snapshots.id"), primary_key=True), sa.Column("team_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String()), sa.Column("members_json", sa.JSON(), nullable=False), sa.Column("raw_config_json", sa.JSON()))
    # Guard historical records from accidental application level UPDATE/DELETE.
    for table in ("snapshots", "snapshot_characters", "snapshot_weapons", "snapshot_artifacts", "snapshot_teams"):
        op.execute(sa.text(f"CREATE TRIGGER immutable_{table}_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END"))
        op.execute(sa.text(f"CREATE TRIGGER immutable_{table}_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END"))

def downgrade():
    for table in ("snapshots", "snapshot_characters", "snapshot_weapons", "snapshot_artifacts", "snapshot_teams"):
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS immutable_{table}_update"))
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS immutable_{table}_delete"))
    op.drop_table("snapshot_teams")
    op.drop_index("ix_snapshot_artifacts_character_key", table_name="snapshot_artifacts")
    op.drop_table("snapshot_artifacts")
    op.drop_table("snapshot_weapons")
    op.drop_table("snapshot_characters")
    op.drop_index("ix_snapshots_account_id", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_table("accounts")
