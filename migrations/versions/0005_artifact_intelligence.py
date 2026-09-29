"""History-preserving manual artifact evaluations and quality config."""
from alembic import op
import sqlalchemy as sa

revision = "0005_artifact_intelligence"
down_revision = "0004_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "artifact_evaluations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False, index=True),
        sa.Column("character_key", sa.String(), nullable=False, index=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.String(), nullable=False, server_default="CONFIRMED"),
        sa.Column("raw_metrics_json", sa.JSON(), nullable=False),
        sa.Column("normalized_metrics_json", sa.JSON(), nullable=False),
        sa.Column("parser_confidence", sa.Float(), nullable=True),
        sa.Column("artifact_fingerprint", sa.String(), nullable=True),
        sa.Column("supersedes_id", sa.String(), sa.ForeignKey("artifact_evaluations.id"), nullable=True),
    )
    op.create_index("ix_artifact_evaluations_latest", "artifact_evaluations", ["account_id", "character_key", "status", "imported_at"])
    op.create_table(
        "artifact_quality_config_versions",
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("artifact_quality_config_versions")
    op.drop_index("ix_artifact_evaluations_latest", table_name="artifact_evaluations")
    op.drop_table("artifact_evaluations")
