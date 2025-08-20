"""create transcription_jobs table

Revision ID: 002_create_transcription_jobs
Revises: 001_create_tables
Create Date: 2024-02-20 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '002_create_transcription_jobs'
down_revision = '001_create_tables'
branch_labels = None
depends_on = None

def table_exists(table_name):
    """Check if a table exists"""
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()

def upgrade() -> None:
    # Create transcription_jobs table if it doesn't exist
    if not table_exists('transcription_jobs'):
        op.create_table(
            'transcription_jobs',
            sa.Column('id', postgresql.UUID(), nullable=False),
            sa.Column('batch_id', postgresql.UUID(), nullable=True),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('original_filename', sa.String(), nullable=True),
            sa.Column('processed_file_path', sa.String(), nullable=True),
            sa.Column('output_file_path', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade() -> None:
    op.drop_table('transcription_jobs') 