"""Make confirmed target imports safe to retry after a lost response."""
from alembic import op
import sqlalchemy as sa

revision = "0009_target_import_idempotency"
down_revision = "0008_snapshot_reference_foreign_keys"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idempotency_receipts",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("request_key", sa.String(length=128), primary_key=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("idempotency_receipts")
