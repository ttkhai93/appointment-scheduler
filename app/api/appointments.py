from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Appointment
from app.schemas import AppointmentCreate, AppointmentOut
from app.services.booking import (
    appointment_query,
    book_appointment,
    get_appointment,
)

router = APIRouter(prefix="/api", tags=["appointments"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=201,
)
async def create_appointment(
    payload: AppointmentCreate,
    db: DbSession,
):
    return await book_appointment(db, payload)


@router.get("/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    db: DbSession,
    dealership_id: int | None = None,
    start_from: Annotated[datetime | None, Query()] = None,
    start_to: Annotated[datetime | None, Query()] = None,
):
    stmt = appointment_query().order_by(Appointment.start_time)
    if dealership_id is not None:
        stmt = stmt.where(Appointment.dealership_id == dealership_id)
    if start_from is not None:
        stmt = stmt.where(Appointment.start_time >= start_from)
    if start_to is not None:
        stmt = stmt.where(Appointment.start_time <= start_to)
    return list((await db.scalars(stmt)).all())


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
async def get_appointment_by_id(
    appointment_id: int,
    db: DbSession,
):
    return await get_appointment(db, appointment_id)
