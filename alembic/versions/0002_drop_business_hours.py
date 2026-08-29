"""drop business_hours

Business hours are now global configuration (same for every dealership and
every day of the week), so the per-dealership table is no longer needed.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("business_hours")


def downgrade() -> None:
    op.create_table(
        "business_hours",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dealership_id",
            sa.Integer(),
            sa.ForeignKey("dealerships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("open_time", sa.Time(), nullable=False),
        sa.Column("close_time", sa.Time(), nullable=False),
        sa.UniqueConstraint(
            "dealership_id", "day_of_week", name="uq_business_hours_dealership_day"
        ),
    )
