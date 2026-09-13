"""Harden durable execution recovery

Revision ID: 4b468990678a
Revises: 490034bcaf74
Create Date: 2026-09-13 18:17:02.935534
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b468990678a"
down_revision: str | Sequence[str] | None = "490034bcaf74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add and safely backfill execution recovery timestamp."""
    op.add_column(
        "execution_records",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE execution_records
            SET updated_at = created_at
            WHERE updated_at IS NULL
            """
        )
    )

    with op.batch_alter_table("execution_records") as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )


def downgrade() -> None:
    """Remove execution recovery timestamp."""
    with op.batch_alter_table("execution_records") as batch_op:
        batch_op.drop_column("updated_at")
