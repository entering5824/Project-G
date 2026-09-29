"""Track partial GOOD coverage and calculated RV for equipped artifacts."""
from alembic import op
import sqlalchemy as sa

revision = "0010_snapshot_coverage_artifact_rv"
down_revision = "0009_target_import_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("snapshots") as batch:
        batch.add_column(sa.Column("coverage_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("effective_state_json", sa.JSON(), nullable=False, server_default="{}"))
    with op.batch_alter_table("snapshot_artifacts") as batch:
        batch.add_column(sa.Column("unactivated_substats_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("rv", sa.Float(), nullable=True))
        batch.add_column(sa.Column("rv_status", sa.String(), nullable=False, server_default="UNKNOWN"))
        batch.add_column(sa.Column("rv_formula_version", sa.String(), nullable=False, server_default="artifact-rv-1"))
    op.create_table(
        "snapshot_material_inventory",
        sa.Column("snapshot_id", sa.String(), sa.ForeignKey("snapshots.id"), primary_key=True),
        sa.Column("material_key", sa.String(), primary_key=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("source_snapshot_id", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("snapshot_material_inventory")
    with op.batch_alter_table("snapshot_artifacts") as batch:
        batch.drop_column("rv_formula_version")
        batch.drop_column("rv_status")
        batch.drop_column("rv")
        batch.drop_column("unactivated_substats_json")
    with op.batch_alter_table("snapshots") as batch:
        batch.drop_column("effective_state_json")
        batch.drop_column("coverage_json")
