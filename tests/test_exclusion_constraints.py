from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Appointment, Customer, ServiceBay, Technician, Vehicle


async def _add_customer_and_vehicle(session):
    customer = Customer(
        email="db-constraint@example.com",
        phone="+84901234567",
        full_name="DB Constraint",
    )
    session.add(customer)
    await session.flush()
    vehicle = Vehicle(
        make="Toyota",
        model="Corolla",
    )
    session.add(vehicle)
    await session.flush()
    await session.commit()
    return customer.id, vehicle.id


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


async def test_exclusion_constraint_allows_back_to_back_appointments(
    db_session, seed_ids
):
    """DB exclusion constraint allows back-to-back appointments ([start, end))."""
    customer_id, vehicle_id = await _add_customer_and_vehicle(db_session)
    technician = await db_session.scalar(select(Technician).limit(1))
    bay = await db_session.scalar(select(ServiceBay).limit(1))
    technician_id = technician.id
    bay_id = bay.id

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


async def test_exclusion_constraint_blocks_technician_overlap_across_bays(
    db_session, seed_ids
):
    """Same technician at overlapping times is rejected even in different bays."""
    customer_id, vehicle_id = await _add_customer_and_vehicle(db_session)
    technicians = list(
        (await db_session.scalars(select(Technician).order_by(Technician.id))).all()
    )
    bays = list(
        (await db_session.scalars(select(ServiceBay).order_by(ServiceBay.id))).all()
    )

    db_session.add(
        _appointment(
            seed_ids,
            customer_id,
            vehicle_id,
            technicians[0].id,
            bays[0].id,
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
            technicians[0].id,
            bays[1].id,
            datetime(2026, 9, 1, 1, 30, tzinfo=UTC),
            datetime(2026, 9, 1, 2, 30, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_exclusion_constraint_blocks_bay_overlap_across_technicians(
    db_session, seed_ids
):
    """Same bay at overlapping times is rejected even with different technicians."""
    customer_id, vehicle_id = await _add_customer_and_vehicle(db_session)
    technicians = list(
        (await db_session.scalars(select(Technician).order_by(Technician.id))).all()
    )
    bay = await db_session.scalar(select(ServiceBay).limit(1))

    db_session.add(
        _appointment(
            seed_ids,
            customer_id,
            vehicle_id,
            technicians[0].id,
            bay.id,
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
            technicians[1].id,
            bay.id,
            datetime(2026, 9, 1, 1, 30, tzinfo=UTC),
            datetime(2026, 9, 1, 2, 30, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
