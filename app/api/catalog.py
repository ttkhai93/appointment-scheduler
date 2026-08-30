from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import (
    DealershipOut,
    ServiceTypeOut,
)
from app.services.catalog import list_dealerships as fetch_dealerships
from app.services.catalog import list_service_types as fetch_service_types

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/dealerships", response_model=list[DealershipOut])
async def list_dealerships(session: DbSession):
    return await fetch_dealerships(session)


@router.get("/service-types", response_model=list[ServiceTypeOut])
async def list_service_types(session: DbSession):
    return await fetch_service_types(session)
