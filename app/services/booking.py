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
from app.services.timeutil import ensure_start_on_slot_boundary, ensure_utc


def ensure_within_business_hours(
    start_utc: datetime,
    end_utc: datetime,
    tz_name: str,
) -> None:
    local_start = start_utc.astimezone(ZoneInfo(tz_name))
    local_end = end_utc.astimezone(local_start.tzinfo)
    if (
        local_start.time() < settings.business_open_time
        or local_end.time() > settings.business_close_time
    ):
        raise DomainValidationError(
            "requested time is outside business hours "
            f"({settings.business_open_time}–{settings.business_close_time} local)"
        )


async def list_qualified_technician_ids(
    session: AsyncSession,
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
    return list((await session.scalars(stmt)).all())


async def list_free_bays(
    session: AsyncSession,
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
    return list((await session.scalars(stmt)).all())


async def list_free_technicians(
    session: AsyncSession,
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
    return list((await session.scalars(stmt)).all())


def appointment_query():
    return select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.technician),
        selectinload(Appointment.service_bay),
        selectinload(Appointment.service_type),
    )


async def list_appointments(
    session: AsyncSession,
    dealership_id: int | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
) -> list[Appointment]:
    stmt = appointment_query().order_by(Appointment.start_time)
    if dealership_id is not None:
        stmt = stmt.where(Appointment.dealership_id == dealership_id)
    if start_from is not None:
        stmt = stmt.where(Appointment.start_time >= start_from)
    if start_to is not None:
        stmt = stmt.where(Appointment.start_time <= start_to)
    return list((await session.scalars(stmt)).all())


async def get_appointment(session: AsyncSession, appointment_id: int) -> Appointment:
    appointment = await session.scalar(
        appointment_query().where(Appointment.id == appointment_id)
    )
    if appointment is None:
        raise NotFoundError(f"appointment {appointment_id} not found")
    return appointment


MAX_BOOKING_ATTEMPTS = 5


async def book_appointment(
    session: AsyncSession,
    payload: AppointmentCreate,
) -> Appointment:
    start_utc = ensure_utc(payload.start_time)
    ensure_start_on_slot_boundary(start_utc, settings.slot_minutes)

    # A concurrent request can take a pair between our availability snapshot
    # and the insert (exclusion constraints reject it). Retry the whole
    # transaction with a fresh snapshot so requests spread across free
    # (bay, technician) pairs instead of failing on the first race.
    for _ in range(MAX_BOOKING_ATTEMPTS):
        dealership = await get_dealership_or_404(session, payload.dealership_id)
        service_type = await get_service_type_or_404(session, payload.service_type_id)
        end_utc = start_utc + timedelta(minutes=service_type.duration_minutes)
        ensure_within_business_hours(start_utc, end_utc, dealership.timezone)

        customer = Customer(
            full_name=payload.customer.full_name,
            email=payload.customer.email.lower(),
            phone=payload.customer.phone,
        )
        session.add(customer)

        vehicle = Vehicle(
            make=payload.vehicle.make,
            model=payload.vehicle.model,
            year=payload.vehicle.year,
            vin=payload.vehicle.vin,
        )
        session.add(vehicle)
        await session.flush()

        technician_ids = await list_qualified_technician_ids(
            session, dealership.id, service_type.id
        )
        if not technician_ids:
            await session.rollback()
            raise BookingConflictError(
                "no_qualified_technician",
                "no technician is qualified for this service type",
            )

        technicians = await list_free_technicians(
            session, technician_ids, start_utc, end_utc
        )
        if not technicians:
            await session.rollback()
            raise BookingConflictError(
                "no_free_technician", "no qualified technician is available"
            )

        bays = await list_free_bays(session, dealership.id, start_utc, end_utc)
        if not bays:
            await session.rollback()
            raise BookingConflictError("no_free_bay", "no service bay is available")

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
        session.add(appointment)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue

        return await get_appointment(session, appointment.id)

    raise BookingConflictError(
        "no_capacity",
        "resources were taken by another request; please retry",
    )
