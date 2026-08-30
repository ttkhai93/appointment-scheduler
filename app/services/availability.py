from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models import (
    Appointment,
    Dealership,
    ServiceBay,
    ServiceType,
    Technician,
)


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
