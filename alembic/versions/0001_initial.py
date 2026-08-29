"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "dealerships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_dealerships_name", "dealerships", ["name"], unique=True)

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

    op.create_table(
        "service_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
    )
    op.create_index("ix_service_types_name", "service_types", ["name"], unique=True)

    op.create_table(
        "technicians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dealership_id",
            sa.Integer(),
            sa.ForeignKey("dealerships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
    )
    op.create_index("ix_technicians_dealership_id", "technicians", ["dealership_id"])

    op.create_table(
        "technician_qualifications",
        sa.Column(
            "technician_id",
            sa.Integer(),
            sa.ForeignKey("technicians.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "service_type_id",
            sa.Integer(),
            sa.ForeignKey("service_types.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "service_bays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dealership_id",
            sa.Integer(),
            sa.ForeignKey("dealerships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
    )
    op.create_index("ix_service_bays_dealership_id", "service_bays", ["dealership_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_vehicles_customer_id", "vehicles", ["customer_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dealership_id",
            sa.Integer(),
            sa.ForeignKey("dealerships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Integer(),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "technician_id",
            sa.Integer(),
            sa.ForeignKey("technicians.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_bay_id",
            sa.Integer(),
            sa.ForeignKey("service_bays.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_type_id",
            sa.Integer(),
            sa.ForeignKey("service_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="confirmed",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"])
    op.create_index(
        "ix_appointments_dealership_start",
        "appointments",
        ["dealership_id", "start_time"],
    )

    # No-overlap guarantees (see design doc §6). `btree_gist` provides the
    # integer equality operators used by the GiST exclusion constraints.
    op.execute(
        """
        ALTER TABLE appointments
        ADD CONSTRAINT uq_appointments_no_bay_overlap
        EXCLUDE USING gist (
            service_bay_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        )
        """
    )
    op.execute(
        """
        ALTER TABLE appointments
        ADD CONSTRAINT uq_appointments_no_tech_overlap
        EXCLUDE USING gist (
            technician_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE appointments DROP CONSTRAINT IF EXISTS uq_appointments_no_tech_overlap"
    )
    op.execute(
        "ALTER TABLE appointments DROP CONSTRAINT IF EXISTS uq_appointments_no_bay_overlap"
    )
    op.drop_table("appointments")
    op.drop_index("ix_vehicles_customer_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_service_bays_dealership_id", table_name="service_bays")
    op.drop_table("service_bays")
    op.drop_table("technician_qualifications")
    op.drop_index("ix_technicians_dealership_id", table_name="technicians")
    op.drop_table("technicians")
    op.drop_index("ix_service_types_name", table_name="service_types")
    op.drop_table("service_types")
    op.drop_table("business_hours")
    op.drop_index("ix_dealerships_name", table_name="dealerships")
    op.drop_table("dealerships")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
