from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Dealership,
    ServiceType,
)


async def list_dealerships(session: AsyncSession) -> list[Dealership]:
    stmt = select(Dealership).order_by(Dealership.id)
    return list((await session.scalars(stmt)).all())


async def list_service_types(session: AsyncSession) -> list[ServiceType]:
    stmt = select(ServiceType).order_by(ServiceType.id)
    return list((await session.scalars(stmt)).all())
