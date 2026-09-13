"""Add policy provenance to runtime audit

Revision ID: a7c1d2e3f4b5
Revises: 4b468990678a
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c1d2e3f4b5"
down_revision: str | Sequence[str] | None = "4b468990678a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist policy provenance with runtime audit evidence."""
    with op.batch_alter_table("runtime_audit_entries") as batch_op:
        batch_op.add_column(
            sa.Column(
                "policy_rule_id",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_authority",
                sa.String(length=100),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_source_name",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_source_version",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_source_reference",
                sa.String(length=500),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_considered_rules",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )

    with op.batch_alter_table("runtime_audit_entries") as batch_op:
        batch_op.alter_column(
            "policy_considered_rules",
            existing_type=sa.JSON(),
            server_default=None,
        )


def downgrade() -> None:
    """Remove policy provenance from runtime audit evidence."""
    with op.batch_alter_table("runtime_audit_entries") as batch_op:
        batch_op.drop_column("policy_considered_rules")
        batch_op.drop_column("policy_source_reference")
        batch_op.drop_column("policy_source_version")
        batch_op.drop_column("policy_source_name")
        batch_op.drop_column("policy_authority")
        batch_op.drop_column("policy_rule_id")
