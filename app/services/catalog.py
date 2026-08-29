from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BusinessHours,
    Dealership,
    ServiceBay,
    ServiceType,
    Technician,
    TechnicianQualification,
)
from app.schemas import (
    BusinessHoursOut,
    TechnicianOut,
    TechnicianQualificationOut,
)


async def list_dealerships(session: AsyncSession) -> list[Dealership]:
    stmt = select(Dealership).order_by(Dealership.id)
    return list((await session.scalars(stmt)).all())


async def list_service_types(session: AsyncSession) -> list[ServiceType]:
    stmt = select(ServiceType).order_by(ServiceType.id)
    return list((await session.scalars(stmt)).all())


async def list_technicians(
    session: AsyncSession,
    dealership_id: int | None = None,
) -> list[TechnicianOut]:
    stmt = (
        select(Technician)
        .options(selectinload(Technician.qualifications))
        .order_by(Technician.id)
    )
    if dealership_id is not None:
        stmt = stmt.where(Technician.dealership_id == dealership_id)
    technicians = list((await session.scalars(stmt)).all())
    return [
        TechnicianOut(
            id=t.id,
            dealership_id=t.dealership_id,
            name=t.name,
            qualification_ids=sorted(st.id for st in t.qualifications),
        )
        for t in technicians
    ]


async def list_technician_qualifications(
    session: AsyncSession,
    dealership_id: int | None = None,
) -> list[TechnicianQualificationOut]:
    stmt = (
        select(
            Technician.id,
            Technician.name,
            ServiceType.id,
            ServiceType.name,
        )
        .join(
            TechnicianQualification,
            TechnicianQualification.technician_id == Technician.id,
        )
        .join(
            ServiceType,
            ServiceType.id == TechnicianQualification.service_type_id,
        )
        .order_by(Technician.id, ServiceType.id)
    )
    if dealership_id is not None:
        stmt = stmt.where(Technician.dealership_id == dealership_id)
    rows = (await session.execute(stmt)).all()
    return [
        TechnicianQualificationOut(
            technician_id=technician_id,
            technician_name=technician_name,
            service_type_id=service_type_id,
            service_type_name=service_type_name,
        )
        for technician_id, technician_name, service_type_id, service_type_name in rows
    ]


async def list_service_bays(
    session: AsyncSession,
    dealership_id: int | None = None,
) -> list[ServiceBay]:
    stmt = select(ServiceBay).order_by(ServiceBay.id)
    if dealership_id is not None:
        stmt = stmt.where(ServiceBay.dealership_id == dealership_id)
    return list((await session.scalars(stmt)).all())


async def list_business_hours(
    session: AsyncSession,
    dealership_id: int | None = None,
) -> list[BusinessHoursOut]:
    stmt = select(BusinessHours).order_by(
        BusinessHours.dealership_id, BusinessHours.day_of_week
    )
    if dealership_id is not None:
        stmt = stmt.where(BusinessHours.dealership_id == dealership_id)
    rows = list((await session.scalars(stmt)).all())
    return [
        BusinessHoursOut(
            id=row.id,
            dealership_id=row.dealership_id,
            day_of_week=row.day_of_week,
            open_time=row.open_time,
            close_time=row.close_time,
        )
        for row in rows
    ]
