from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DbSession
from app.schemas import AppointmentCreate, AppointmentOut
from app.services.booking import (
    book_appointment,
    get_appointment,
)
from app.services.booking import (
    list_appointments as fetch_appointments,
)

router = APIRouter(prefix="/api", tags=["appointments"])


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=201,
)
async def create_appointment(
    payload: AppointmentCreate,
    session: DbSession,
):
    return await book_appointment(session, payload)


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    session: DbSession,
    dealership_id: int | None = None,
    start_from: Annotated[datetime | None, Query()] = None,
    start_to: Annotated[datetime | None, Query()] = None,
):
    return await fetch_appointments(session, dealership_id, start_from, start_to)


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
async def get_appointment_by_id(
    appointment_id: int,
    session: DbSession,
):
    return await get_appointment(session, appointment_id)
