"""Store manually curated per-account TierPack versions."""
from alembic import op
import sqlalchemy as sa

revision = "0018_tier_pack"
down_revision = "0017_remove_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("tier_pack_versions",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("pack_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_table("tier_pack_versions")
