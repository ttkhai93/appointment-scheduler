from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models import Dealership, ServiceBay, ServiceType, Technician
from app.schemas import (
    DealershipOut,
    ServiceBayOut,
    ServiceTypeOut,
    TechnicianOut,
)

router = APIRouter(prefix="/api", tags=["catalog"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/dealerships", response_model=list[DealershipOut])
async def list_dealerships(db: DbSession):
    return list((await db.scalars(select(Dealership).order_by(Dealership.id))).all())


@router.get("/service-types", response_model=list[ServiceTypeOut])
async def list_service_types(db: DbSession):
    return list((await db.scalars(select(ServiceType).order_by(ServiceType.id))).all())


@router.get("/technicians", response_model=list[TechnicianOut])
async def list_technicians(
    db: DbSession,
    dealership_id: int | None = None,
):
    stmt = (
        select(Technician)
        .options(selectinload(Technician.qualifications))
        .order_by(Technician.id)
    )
    if dealership_id is not None:
        stmt = stmt.where(Technician.dealership_id == dealership_id)
    technicians = list((await db.scalars(stmt)).all())
    return [
        TechnicianOut(
            id=t.id,
            dealership_id=t.dealership_id,
            name=t.name,
            qualification_ids=sorted(st.id for st in t.qualifications),
        )
        for t in technicians
    ]


@router.get("/service-bays", response_model=list[ServiceBayOut])
async def list_service_bays(
    db: DbSession,
    dealership_id: int | None = None,
):
    stmt = select(ServiceBay).order_by(ServiceBay.id)
    if dealership_id is not None:
        stmt = stmt.where(ServiceBay.dealership_id == dealership_id)
    return list((await db.scalars(stmt)).all())
