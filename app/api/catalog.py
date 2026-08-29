from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import DealershipOut, ServiceBayOut, ServiceTypeOut, TechnicianOut
from app.services.catalog import (
    list_dealerships as fetch_dealerships,
)
from app.services.catalog import (
    list_service_bays as fetch_service_bays,
)
from app.services.catalog import (
    list_service_types as fetch_service_types,
)
from app.services.catalog import (
    list_technicians as fetch_technicians,
)

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/dealerships", response_model=list[DealershipOut])
async def list_dealerships(session: DbSession):
    return await fetch_dealerships(session)


@router.get("/service-types", response_model=list[ServiceTypeOut])
async def list_service_types(session: DbSession):
    return await fetch_service_types(session)


@router.get("/technicians", response_model=list[TechnicianOut])
async def list_technicians(
    session: DbSession,
    dealership_id: int | None = None,
):
    return await fetch_technicians(session, dealership_id)


@router.get("/service-bays", response_model=list[ServiceBayOut])
async def list_service_bays(
    session: DbSession,
    dealership_id: int | None = None,
):
    return await fetch_service_bays(session, dealership_id)
