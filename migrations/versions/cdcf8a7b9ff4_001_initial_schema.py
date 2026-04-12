"""001_initial_schema

Revision ID: cdcf8a7b9ff4
Revises:
Create Date: 2026-04-11 23:42:18.313711

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "cdcf8a7b9ff4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables: invoices and extraction_logs."""
    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("workflow_id", sa.String(), nullable=True, unique=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "EXTRACTING", "VALIDATING", "COMPLETED", "FAILED", name="invoicestatus"),
                  nullable=False, default="PENDING"),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "extraction_logs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column("invoice_id", sa.UUID(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop tables."""
    op.drop_table("extraction_logs")
    op.drop_table("invoices")