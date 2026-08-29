from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import BookingConflictError, DomainValidationError, NotFoundError
from app.models import (
    Appointment,
    BusinessHours,
    Customer,
    ServiceBay,
    Technician,
    TechnicianQualification,
    Vehicle,
)
from app.schemas import AppointmentCreate
from app.services.availability import (
    bay_overlap_subquery,
    get_dealership_or_404,
    get_service_type_or_404,
    qualified_technician_overlap_subquery,
)
from app.services.timeutil import ensure_utc, validate_grid


async def upsert_customer(db: AsyncSession, data) -> Customer:
    """Create or update a customer by (lowercased) email."""
    email = data.email.lower()
    customer = await db.scalar(select(Customer).where(Customer.email == email))
    if customer is None:
        customer = Customer(
            full_name=data.full_name,
            email=email,
            phone=data.phone,
        )
        db.add(customer)
    else:
        customer.full_name = data.full_name
        customer.phone = data.phone
    await db.flush()
    return customer


async def ensure_within_business_hours(
    db: AsyncSession,
    dealership,
    start_utc: datetime,
    end_utc: datetime,
) -> None:
    local_start = start_utc.astimezone(ZoneInfo(dealership.timezone))
    local_end = end_utc.astimezone(local_start.tzinfo)
    business_hours = await db.scalar(
        select(BusinessHours).where(
            BusinessHours.dealership_id == dealership.id,
            BusinessHours.day_of_week == local_start.weekday(),
        )
    )
    if business_hours is None:
        raise DomainValidationError("dealership is closed on this day")
    if (
        local_start.time() < business_hours.open_time
        or local_end.time() > business_hours.close_time
    ):
        raise DomainValidationError(
            "requested time is outside business hours "
            f"({business_hours.open_time}–{business_hours.close_time} local)"
        )


async def list_qualified_technician_ids(
    db: AsyncSession,
    dealership_id: int,
    service_type_id: int,
) -> list[int]:
    stmt = (
        select(Technician.id)
        .join(
            TechnicianQualification,
            TechnicianQualification.technician_id == Technician.id,
        )
        .where(
            Technician.dealership_id == dealership_id,
            TechnicianQualification.service_type_id == service_type_id,
        )
        .order_by(Technician.id)
    )
    return list((await db.scalars(stmt)).all())


async def list_free_bays(
    db: AsyncSession,
    dealership_id: int,
    start: datetime,
    end: datetime,
) -> list[ServiceBay]:
    overlapping = bay_overlap_subquery(start, end)
    stmt = (
        select(ServiceBay)
        .where(ServiceBay.dealership_id == dealership_id, ~overlapping)
        .order_by(ServiceBay.id)
    )
    return list((await db.scalars(stmt)).all())


async def list_free_technicians(
    db: AsyncSession,
    technician_ids: list[int],
    start: datetime,
    end: datetime,
) -> list[Technician]:
    overlapping = qualified_technician_overlap_subquery(start, end)
    stmt = (
        select(Technician)
        .where(Technician.id.in_(technician_ids), ~overlapping)
        .order_by(Technician.id)
    )
    return list((await db.scalars(stmt)).all())


def appointment_query():
    return select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.technician),
        selectinload(Appointment.service_bay),
        selectinload(Appointment.service_type),
    )


async def get_appointment(db: AsyncSession, appointment_id: int) -> Appointment:
    appointment = await db.scalar(
        appointment_query().where(Appointment.id == appointment_id)
    )
    if appointment is None:
        raise NotFoundError(f"appointment {appointment_id} not found")
    return appointment


MAX_BOOKING_ATTEMPTS = 5


async def book_appointment(
    db: AsyncSession,
    payload: AppointmentCreate,
) -> Appointment:
    start_utc = ensure_utc(payload.start_time)
    validate_grid(start_utc, settings.slot_minutes)

    # A concurrent request can take a pair between our availability snapshot
    # and the insert (exclusion constraints reject it). Retry the whole
    # transaction with a fresh snapshot so requests spread across free
    # (bay, technician) pairs instead of failing on the first race.
    for _ in range(MAX_BOOKING_ATTEMPTS):
        dealership = await get_dealership_or_404(db, payload.dealership_id)
        service_type = await get_service_type_or_404(db, payload.service_type_id)
        end_utc = start_utc + timedelta(minutes=service_type.duration_minutes)
        await ensure_within_business_hours(db, dealership, start_utc, end_utc)

        customer = await upsert_customer(db, payload.customer)
        vehicle = Vehicle(
            customer_id=customer.id,
            make=payload.vehicle.make,
            model=payload.vehicle.model,
            year=payload.vehicle.year,
            vin=payload.vehicle.vin,
        )
        db.add(vehicle)
        await db.flush()

        technician_ids = await list_qualified_technician_ids(
            db, dealership.id, service_type.id
        )
        if not technician_ids:
            await db.rollback()
            raise BookingConflictError(
                "no_qualified_technician",
                "no technician is qualified for this service type",
            )

        bays = await list_free_bays(db, dealership.id, start_utc, end_utc)
        if not bays:
            await db.rollback()
            raise BookingConflictError("no_free_bay", "no service bay is available")

        technicians = await list_free_technicians(
            db, technician_ids, start_utc, end_utc
        )
        if not technicians:
            await db.rollback()
            raise BookingConflictError(
                "no_free_technician", "no qualified technician is available"
            )

        appointment = Appointment(
            dealership_id=dealership.id,
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            technician_id=technicians[0].id,
            service_bay_id=bays[0].id,
            service_type_id=service_type.id,
            start_time=start_utc,
            end_time=end_utc,
            status="confirmed",
        )
        db.add(appointment)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue

        return await get_appointment(db, appointment.id)

    raise BookingConflictError(
        "no_capacity",
        "resources were taken by another request; please retry",
    )
