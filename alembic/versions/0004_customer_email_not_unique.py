"""drop unique constraint on customers.email

Customers are now created per booking (like vehicles), so multiple bookings
by the same email address must be allowed.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_customers_email", table_name="customers")


def downgrade() -> None:
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)
