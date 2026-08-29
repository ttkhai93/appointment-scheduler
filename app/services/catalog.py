from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Dealership, ServiceBay, ServiceType, Technician
from app.schemas import TechnicianOut


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


async def list_service_bays(
    session: AsyncSession,
    dealership_id: int | None = None,
) -> list[ServiceBay]:
    stmt = select(ServiceBay).order_by(ServiceBay.id)
    if dealership_id is not None:
        stmt = stmt.where(ServiceBay.dealership_id == dealership_id)
    return list((await session.scalars(stmt)).all())
