from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundError
from app.models import (
    Appointment,
    Dealership,
    ServiceBay,
    ServiceType,
    Technician,
    TechnicianQualification,
)
from app.schemas import AvailabilityResponse, AvailabilitySlot
from app.services.timeutil import business_day_slots, ensure_utc, validate_grid


async def get_dealership_or_404(
    session: AsyncSession, dealership_id: int
) -> Dealership:
    dealership = await session.get(Dealership, dealership_id)
    if dealership is None:
        raise NotFoundError(f"dealership {dealership_id} not found")
    return dealership


async def get_service_type_or_404(
    session: AsyncSession, service_type_id: int
) -> ServiceType:
    service_type = await session.get(ServiceType, service_type_id)
    if service_type is None:
        raise NotFoundError(f"service type {service_type_id} not found")
    return service_type


def qualified_technician_overlap_subquery(start: datetime, end: datetime):
    return (
        select(Appointment.id)
        .where(
            Appointment.technician_id == Technician.id,
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
        .exists()
    )


def bay_overlap_subquery(start: datetime, end: datetime):
    return (
        select(Appointment.id)
        .where(
            Appointment.service_bay_id == ServiceBay.id,
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
        .exists()
    )


async def free_qualified_technician_exists(
    session: AsyncSession,
    dealership_id: int,
    service_type_id: int,
    start: datetime,
    end: datetime,
) -> bool:
    overlapping = qualified_technician_overlap_subquery(start, end)
    stmt = (
        select(Technician.id)
        .join(
            TechnicianQualification,
            TechnicianQualification.technician_id == Technician.id,
        )
        .where(
            Technician.dealership_id == dealership_id,
            TechnicianQualification.service_type_id == service_type_id,
            ~overlapping,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def free_bay_exists(
    session: AsyncSession,
    dealership_id: int,
    start: datetime,
    end: datetime,
) -> bool:
    overlapping = bay_overlap_subquery(start, end)
    stmt = (
        select(ServiceBay.id)
        .where(
            ServiceBay.dealership_id == dealership_id,
            ~overlapping,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def check_slot(
    session: AsyncSession,
    dealership_id: int,
    service_type_id: int,
    start: datetime,
    end: datetime,
) -> bool:
    return await free_qualified_technician_exists(
        session, dealership_id, service_type_id, start, end
    ) and await free_bay_exists(session, dealership_id, start, end)


async def list_free_slots(
    session: AsyncSession,
    dealership_id: int,
    service_type_id: int,
    day: date,
) -> AvailabilityResponse:
    dealership = await get_dealership_or_404(session, dealership_id)
    service_type = await get_service_type_or_404(session, service_type_id)

    candidate_slots = business_day_slots(
        day,
        settings.business_open_time,
        settings.business_close_time,
        dealership.timezone,
        service_type.duration_minutes,
        settings.slot_minutes,
    )
    free_slots: list[AvailabilitySlot] = []
    for start, end in candidate_slots:
        if await check_slot(session, dealership_id, service_type_id, start, end):
            free_slots.append(AvailabilitySlot(start_time=start, end_time=end))
    return AvailabilityResponse(
        date=day, service_type_id=service_type_id, slots=free_slots
    )


async def check_start_time(
    session: AsyncSession,
    dealership_id: int,
    service_type_id: int,
    start_time: datetime,
) -> tuple[bool, str | None]:
    """Advisory real-time check for a specific start time."""
    start = ensure_utc(start_time)
    validate_grid(start, settings.slot_minutes)
    service_type = await get_service_type_or_404(session, service_type_id)
    await get_dealership_or_404(session, dealership_id)
    end = start + timedelta(minutes=service_type.duration_minutes)
    if await check_slot(session, dealership_id, service_type_id, start, end):
        return True, None
    if not await free_qualified_technician_exists(
        session, dealership_id, service_type_id, start, end
    ):
        return False, "no_qualified_technician"
    return False, "no_free_bay"
