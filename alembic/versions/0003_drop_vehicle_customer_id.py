"""drop vehicles.customer_id

Vehicles are appointment-attached value objects (free-form car details created
per booking) rather than customer-owned entities, so the ownership column is no
longer needed. The booking's customer is already on appointments.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_vehicles_customer_id", table_name="vehicles")
    op.drop_constraint("vehicles_customer_id_fkey", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "customer_id")


def downgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column("customer_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE vehicles v
        SET customer_id = a.customer_id
        FROM appointments a
        WHERE a.vehicle_id = v.id
        """
    )
    op.alter_column("vehicles", "customer_id", nullable=False)
    op.create_foreign_key(
        "vehicles_customer_id_fkey",
        "vehicles",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_vehicles_customer_id", "vehicles", ["customer_id"])
