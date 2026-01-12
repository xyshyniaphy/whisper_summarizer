"""add segments_path column

Revision ID: 002_add_segments_path
Revises: 001_add_runner_status
Create Date: 2025-01-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_segments_path'
down_revision = '001_add_runner_status'
branch_labels = None
depends_on = None


def upgrade():
    # Add segments_path column for preserving Whisper timestamps
    op.add_column('transcriptions', sa.Column('segments_path', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('transcriptions', 'segments_path')
