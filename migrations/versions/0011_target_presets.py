"""Add independently versioned build presets and an active preset per character."""
from alembic import op
import sqlalchemy as sa

revision = "0011_target_presets"
down_revision = "0010_snapshot_coverage_artifact_rv"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("character_target_versions") as batch:
        batch.add_column(sa.Column("preset_key", sa.String(), nullable=False, server_default="default"))

    op.create_table(
        "character_target_presets",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("character_key", sa.String(), primary_key=True),
        sa.Column("preset_key", sa.String(), primary_key=True),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO character_target_presets (account_id, character_key, preset_key, label, is_active)
        SELECT account_id, character_key, 'default', 'Default', 1
        FROM character_target_versions
        GROUP BY account_id, character_key
    """))
    op.create_index("uq_target_preset_active", "character_target_presets",
        ["account_id", "character_key"], unique=True,
        sqlite_where=sa.text("is_active = 1"))


def downgrade():
    op.drop_index("uq_target_preset_active", table_name="character_target_presets")
    op.drop_table("character_target_presets")
    with op.batch_alter_table("character_target_versions") as batch:
        batch.drop_column("preset_key")
