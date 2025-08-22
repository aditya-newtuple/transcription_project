"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ---- Create enum types ----
    conn.execute(sa.text("CREATE TYPE job_status AS ENUM ('queued','running','succeeded','failed','canceled')"))
    conn.execute(sa.text("CREATE TYPE transcript_format AS ENUM ('txt','srt')"))
    conn.execute(sa.text("CREATE TYPE batch_status AS ENUM ('created','queued','running','completed','failed','canceled')"))

    # ---- Create tables ----
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "created",
                "queued",
                "running",
                "completed",
                "failed",
                "canceled",
                name="batch_status",
                create_type=False,
            ),
            nullable=False,
            server_default="created",
        ),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("message", sa.Text()),
    )

    op.create_table(
        "file",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("source_name", sa.String()),
        sa.Column("path", sa.String()),
        sa.Column("mime_type", sa.String()),
        sa.Column("bytes", sa.BigInteger()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "succeeded",
                "failed",
                "canceled",
                name="job_status",
                create_type=False,
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("queued_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("message", sa.Text()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("file_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "format",
            postgresql.ENUM(
                "txt",
                "srt",
                name="transcript_format",
                create_type=False,
            ),
            nullable=False,
            server_default="txt",
        ),
        sa.Column("content", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("approved_by", sa.BigInteger()),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["file_id"], ["file.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("file_id", "version", "format", name="uq_file_version_format"),
    )

    # ---- Create indexes ----
    op.create_index("idx_jobs_created_by", "jobs", ["created_by"])
    op.create_index("idx_jobs_status", "jobs", ["status"])
    op.create_index("idx_jobs_created_at", "jobs", ["created_at"])

    op.create_index("idx_file_job_id", "file", ["job_id"])
    op.create_index("idx_file_status", "file", ["status"])
    op.create_index("idx_file_created_by", "file", ["created_by"])

    op.create_index(
        "idx_transcripts_file_approved", "transcripts", ["file_id", "is_approved"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_transcripts_file_approved", table_name="transcripts")
    op.drop_index("idx_file_created_by", table_name="file")
    op.drop_index("idx_file_status", table_name="file")
    op.drop_index("idx_file_job_id", table_name="file")
    op.drop_index("idx_jobs_created_at", table_name="jobs")
    op.drop_index("idx_jobs_status", table_name="jobs")
    op.drop_index("idx_jobs_created_by", table_name="jobs")

    # Drop tables
    op.drop_table("transcripts")
    op.drop_table("file")
    op.drop_table("jobs")

    # Drop enum types
    conn = op.get_bind()
    conn.execute(sa.text("DROP TYPE IF EXISTS job_status CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS transcript_format CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS batch_status CASCADE")) 