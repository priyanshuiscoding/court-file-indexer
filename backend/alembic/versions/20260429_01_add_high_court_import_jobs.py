"""add high court import jobs table

Revision ID: 20260429_01
Revises:
Create Date: 2026-04-29 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260429_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "high_court_import_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(length=128), nullable=False, server_default="high_court_mysql"),
        sa.Column("external_row_id", sa.String(length=128), nullable=True),
        sa.Column("batch_no", sa.String(length=128), nullable=False),
        sa.Column("fil_no", sa.String(length=128), nullable=True),
        sa.Column("source_pdf_path", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="DISCOVERED"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("import_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hc_import_jobs_source_system", "high_court_import_jobs", ["source_system"], unique=False)
    op.create_index("ix_hc_import_jobs_external_row_id", "high_court_import_jobs", ["external_row_id"], unique=False)
    op.create_index("ix_hc_import_jobs_batch_no", "high_court_import_jobs", ["batch_no"], unique=False)
    op.create_index("ix_hc_import_jobs_fil_no", "high_court_import_jobs", ["fil_no"], unique=False)
    op.create_index("ix_hc_import_jobs_document_id", "high_court_import_jobs", ["document_id"], unique=False)
    op.create_index("ix_hc_import_jobs_status", "high_court_import_jobs", ["status"], unique=False)
    op.create_index("ux_hc_import_jobs_batch_no", "high_court_import_jobs", ["batch_no"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_hc_import_jobs_batch_no", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_status", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_document_id", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_fil_no", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_batch_no", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_external_row_id", table_name="high_court_import_jobs")
    op.drop_index("ix_hc_import_jobs_source_system", table_name="high_court_import_jobs")
    op.drop_table("high_court_import_jobs")
