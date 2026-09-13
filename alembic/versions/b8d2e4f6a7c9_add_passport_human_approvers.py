"""Add human approvers to Safety Passport.

Revision ID: b8d2e4f6a7c9
Revises: a7c1d2e3f4b5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8d2e4f6a7c9"
down_revision: str | Sequence[str] | None = "a7c1d2e3f4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist the approver set bound into signed Safety Passports."""
    with op.batch_alter_table("safety_passports") as batch_op:
        batch_op.add_column(
            sa.Column(
                "human_approvers",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )

    with op.batch_alter_table("safety_passports") as batch_op:
        batch_op.alter_column(
            "human_approvers",
            existing_type=sa.JSON(),
            server_default=None,
        )


def downgrade() -> None:
    """Remove persisted Safety Passport approvers."""
    with op.batch_alter_table("safety_passports") as batch_op:
        batch_op.drop_column("human_approvers")
