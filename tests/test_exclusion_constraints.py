from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Appointment, Customer, ServiceBay, Technician, Vehicle


def _appointment(
    seed_ids,
    customer_id,
    vehicle_id,
    technician_id,
    bay_id,
    start,
    end,
):
    return Appointment(
        dealership_id=seed_ids["dealership_id"],
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        technician_id=technician_id,
        service_bay_id=bay_id,
        service_type_id=seed_ids["oil_change_id"],
        start_time=start,
        end_time=end,
        status="confirmed",
    )


async def test_exclusion_constraint_blocks_overlap(db_session, seed_ids):
    customer = Customer(
        email="db-constraint@example.com",
        phone="+84901234567",
        full_name="DB Constraint",
    )
    db_session.add(customer)
    await db_session.flush()
    vehicle = Vehicle(
        customer_id=customer.id,
        make="Toyota",
        model="Corolla",
    )
    db_session.add(vehicle)
    await db_session.flush()
    await db_session.commit()
    customer_id = customer.id
    vehicle_id = vehicle.id
    technician = await db_session.scalar(select(Technician).limit(1))
    bay = await db_session.scalar(select(ServiceBay).limit(1))
    technician_id = technician.id
    bay_id = bay.id

    # Insert rows behind the ORM's back to test the DB constraint directly.
    db_session.add(
        _appointment(
            seed_ids,
            customer_id,
            vehicle_id,
            technician_id,
            bay_id,
            datetime(2026, 9, 1, 1, 0, tzinfo=UTC),
            datetime(2026, 9, 1, 2, 0, tzinfo=UTC),
        )
    )
    await db_session.flush()

    db_session.add(
        _appointment(
            seed_ids,
            customer_id,
            vehicle_id,
            technician_id,
            bay_id,
            datetime(2026, 9, 1, 1, 30, tzinfo=UTC),
            datetime(2026, 9, 1, 2, 30, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # Adjacent appointments ([start, end)) are NOT a conflict.
    db_session.add(
        _appointment(
            seed_ids,
            customer_id,
            vehicle_id,
            technician_id,
            bay_id,
            datetime(2026, 9, 1, 2, 0, tzinfo=UTC),
            datetime(2026, 9, 1, 3, 0, tzinfo=UTC),
        )
    )
    await db_session.flush()
