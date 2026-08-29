from datetime import date, datetime

from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import AvailabilityCheckResponse, AvailabilityResponse
from app.services.availability import check_start_time, list_free_slots

router = APIRouter(prefix="/api", tags=["availability"])


@router.get("/availability", response_model=AvailabilityResponse)
async def availability(
    session: DbSession,
    dealership_id: int,
    service_type_id: int,
    date: date,
):
    """List free slots for a date (interpreted in the dealership's timezone)."""
    return await list_free_slots(session, dealership_id, service_type_id, date)


@router.get("/availability/check", response_model=AvailabilityCheckResponse)
async def availability_check(
    session: DbSession,
    dealership_id: int,
    service_type_id: int,
    start_time: datetime,
):
    """Advisory real-time check for a specific start time."""
    available, reason = await check_start_time(
        session, dealership_id, service_type_id, start_time
    )
    return AvailabilityCheckResponse(available=available, reason=reason)
