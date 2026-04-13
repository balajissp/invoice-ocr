"""002_add_ocr_fields

Revision ID: 0c11a60ce013
Revises: cdcf8a7b9ff4
Create Date: 2026-04-11 23:57:37.880215

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c11a60ce013"
down_revision: Union[str, Sequence[str], None] = "cdcf8a7b9ff4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OCR-related columns and update status enum."""
    # Add new columns to invoices
    op.add_column("invoices", sa.Column("raw_ocr_output", sa.Text(), nullable=True))
    op.add_column(
        "invoices", sa.Column("extraction_confidence", sa.JSON(), nullable=True)
    )
    op.add_column("invoices", sa.Column("file_type", sa.String(10), nullable=True))

    # Update enum to include PARTIAL
    op.execute("ALTER TYPE invoicestatus ADD VALUE 'PARTIAL'")


def downgrade() -> None:
    """Revert OCR changes."""
    op.drop_column("invoices", "file_type")
    op.drop_column("invoices", "extraction_confidence")
    op.drop_column("invoices", "raw_ocr_output")

    # op.execute("ALTER TYPE invoicestatus REMOVE VALUE 'PARTIAL'") # can't remove enums in pgsql :(
