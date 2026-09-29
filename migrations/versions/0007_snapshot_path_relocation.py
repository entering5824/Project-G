"""Allow relocating immutable snapshots during validated local restore."""
from alembic import op
import sqlalchemy as sa

revision = "0007_snapshot_path_relocation"
down_revision = "0006_history_events"
branch_labels = None
depends_on = None


def upgrade():
    # Snapshot game state remains immutable. Only its machine-local raw file
    # location may change when restoring a backup to another data directory.
    op.execute(sa.text("DROP TRIGGER IF EXISTS immutable_snapshots_update"))
    op.execute(sa.text("""
        CREATE TRIGGER immutable_snapshots_update
        BEFORE UPDATE OF id, account_id, imported_at, good_format, good_version,
            good_db_version, raw_file_hash, canonical_state_hash,
            previous_snapshot_id, importer_version
        ON snapshots
        BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END
    """))


def downgrade():
    op.execute(sa.text("DROP TRIGGER IF EXISTS immutable_snapshots_update"))
    op.execute(sa.text("""
        CREATE TRIGGER immutable_snapshots_update BEFORE UPDATE ON snapshots
        BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END
    """))
