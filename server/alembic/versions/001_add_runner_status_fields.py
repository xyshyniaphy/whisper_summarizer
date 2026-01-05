"""add runner status fields

Revision ID: 001_add_runner_status
Revises:
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_runner_status'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for server/runner architecture
    op.add_column('transcriptions', sa.Column('status', sa.String(20), nullable=True, server_default='pending'))
    op.add_column('transcriptions', sa.Column('runner_id', sa.String(100), nullable=True))
    op.add_column('transcriptions', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('transcriptions', sa.Column('processing_time_seconds', sa.Integer(), nullable=True))

    # Create indexes for runner queries
    op.create_index('idx_transcriptions_status', 'transcriptions', ['status'])
    op.create_index('idx_transcriptions_status_created', 'transcriptions', ['status', 'created_at'])

    # Update existing records:
    # - completed/failed stage -> keep as status
    # - other stages -> pending
    op.execute("""
        UPDATE transcriptions
        SET status = CASE
            WHEN stage = 'completed' THEN 'completed'
            WHEN stage = 'failed' THEN 'failed'
            ELSE 'pending'
        END
        WHERE status IS NULL
    """)

    # Make status non-nullable after update
    op.alter_column('transcriptions', 'status', nullable=False)


def downgrade():
    # Remove indexes
    op.drop_index('idx_transcriptions_status_created', table_name='transcriptions')
    op.drop_index('idx_transcriptions_status', table_name='transcriptions')

    # Remove columns
    op.drop_column('transcriptions', 'processing_time_seconds')
    op.drop_column('transcriptions', 'started_at')
    op.drop_column('transcriptions', 'runner_id')
    op.drop_column('transcriptions', 'status')
