"""Protect account and snapshot reference columns from dangling snapshot IDs."""
from alembic import op

revision = "0008_snapshot_reference_foreign_keys"
down_revision = "0007_snapshot_path_relocation"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_accounts_current_snapshot_id_snapshots",
            "snapshots", ["current_snapshot_id"], ["id"],
        )
    with op.batch_alter_table("snapshots", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_snapshots_previous_snapshot_id_snapshots",
            "snapshots", ["previous_snapshot_id"], ["id"],
        )


def downgrade():
    with op.batch_alter_table("snapshots", recreate="always") as batch:
        batch.drop_constraint("fk_snapshots_previous_snapshot_id_snapshots", type_="foreignkey")
    with op.batch_alter_table("accounts", recreate="always") as batch:
        batch.drop_constraint("fk_accounts_current_snapshot_id_snapshots", type_="foreignkey")
